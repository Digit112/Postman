import math
import random
import json
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont

# This file implements the mail simulation backend

# Function that reads a json file and returns an object representing the data
def load_json(fn):
	fin = open(fn, "r")
	x = json.loads(fin.read(), object_hook=lambda d: SimpleNamespace(**d))
	fin.close()
	return x

# This class tracks the gamestate, including a list of all senders, the post network shape, and all mail in transit.
class postman:
	# The postman initializer creates the game map and all the senders.
	def __init__(self, serv):
		# Load settings
		self.settings = load_json("settings.json")
		
		# Load list of days (rulesets)
		self.days = load_json("servers/" + serv + "/days.json")
		
		# Load server settings
		self.srv = load_json("servers/" + serv + "/server.json")
		
		# Set starting day
		self.day = self.days[0]

		# Load localization file
		self.strings = load_json("localization/" + self.settings.language + ".json")
		
		# Each new piece of mail has a unique ID. This number tracks what the next available ID is.
		self.next_mail_ID = random.randrange(0, 1000)
		
		# Load town name list
		fin = open("servers/" + serv + "/names/town_names.txt", "r")
		self.town_names = fin.read().split("\n")
		fin.close()
		
		# Load street name list
		fin = open("servers/" + serv + "/names/street_names.txt", "r")
		self.street_names = fin.read().split("\n")
		fin.close()
		
		# Load first name list
		fin = open("servers/" + serv + "/names/first_names.txt", "r")
		self.first_names = fin.read().split("\n")
		fin.close()
		
		# Load last name list
		fin = open("servers/" + serv + "/names/last_names.txt", "r")
		self.last_names = fin.read().split("\n")
		fin.close()
		
		# Start the game in simulation mode. Player input is ignored at this time.
		self.is_simulating = True
		
		# Initialize list of all senders in the game
		self.senders = []
		
		# Initialize list for all mail in transit
		self.post = []
		
		# Initialize list of towns
		self.towns = []
		
		# Initialize routing table
		self.routing = {}
	
	# Generate a random piece of mail somewhere.
	def gen_mail(self):
		sender = random.choice(self.senders)
		recipient = None
		
		# Mail has a chance to be in reply to an individual from whom mail was recently received
		if random.uniform(0, 1) < 0.5 and len(sender.recv_from) > 0:
			recipient = random.choice(sender.recv_from)
		
		# Mail has a good chance of being addressed to someone within the sender's town
		elif random.uniform(0, 1) < 0.6:
			while True:
				recipient = random.choice(sender.town.citizens)
				
				# Ensure the recipient is not the sender
				if recipient != sender:
					break
		
		# If both previous conditions failed, just pick a random person anywhere.
		else:
			while True:
				recipient = random.choice(self.senders)
				
				# Ensure the recipient is not the sender
				if recipient != sender:
					break
		
		mail_item = mail(self, sender, recipient, False)
		self.post.append(mail_item)
		sender.add_mail(mail_item)
			
	# Generates a town. pop_mul is a multiplier for the average population. Actual population varies a lot.
	# Towns of pop_mul 1 will have an average population of 80.
	def add_town(self, pop_mul, x, y, player_ctrl):
		return town(self, pop_mul, x, y, player_ctrl)
	
	# Generates the game world according to the settings. Towns must be at least 50
	def gen_map(self):
		# Generate the player's town
		self.towns.append(self.add_town(0.5, 0, 0, True))
		
		# Generate connecting towns
		for i in range(0, self.settings.world_gen.num_connecting_towns):
			# Town size is based on which town is being generated
			t_size = 0.5
			if i == 1:
				t_size = 1.8
			elif i == 2:
				t_size = 0.8
			
			# Continuously generate coordinates until either minimum town separation is satisfied or the number of tries is exhausted.
			# If a town exhausts all attempts, stop generating connecting towns.
			gen_successful = False
			for j in range(400):
				angle = random.uniform(0, 2*math.pi)
				radius = random.uniform(self.settings.world_gen.min_town_sep, 300)
				
				x = radius * math.cos(radius)
				y = radius * math.sin(radius)
				
				coords_valid = True
				for t in self.towns[1:]:
					if ((t.x - x)**2 + (t.y - y)**2)**0.5 < self.settings.world_gen.min_town_sep:
						coords_valid = False
						break
				
				if coords_valid:
					gen_successful = True
					break
			
			if gen_successful:
				self.towns.append(self.add_town(t_size, x, y, False))
				postman.connect_towns(self.towns[0], self.towns[-1])
			else:
				print("Couldn't find room for all connecting towns; Number of connecting towns does not reflect settings.")
				break
		
		# Generate additional towns
		for i in range(0, self.settings.world_gen.num_additional_towns):
			# Continuously generate coordinates until either minimum town separation is satisfied or the number of tries is exhausted.
			# If a town exhausts all attempts, stop generating connecting towns.
			gen_successful = False
			for j in range(400):
				angle = random.uniform(0, 2*math.pi)
				radius = random.uniform(280, 1060)
				
				x = radius * math.cos(radius)
				y = radius * math.sin(radius)
				
				if y < -510 or y > 510 or x < -930 or x > 930:
					continue
				
				coords_valid = True
				min_town = None
				min_dist = 3000
				for t in self.towns[1:]:
					cur_dist = ((t.x - x)**2 + (t.y - y)**2)**0.5
					if cur_dist < self.settings.world_gen.min_town_sep:
						coords_valid = False
						break
					
					if cur_dist < min_dist:
						min_dist = cur_dist
						min_town = t
				
				if coords_valid:
					gen_successful = True
					break
			
			if gen_successful:
				self.towns.append(self.add_town(random.uniform(0.3, 1.2), x, y, False))
				postman.connect_towns(min_town, self.towns[-1])
			else:
				print("Couldn't find room for all additional towns; Number of additional towns does not reflect settings.")
				break
		
		# Optimize routes. Consider town A, connected to B, connected to C: A-B-C
		# If the distance B-A-C is shorter, replace the old connection with it.
		for a_i in range(1, len(self.towns)):
			a = self.towns[a_i]
			
			b_i_off = 0
			for b_i in range(len(a.neighbors)):
				b = a.neighbors[b_i - b_i_off]
				if b == self.towns[0]:
					continue
				
				c_i_off = 0
				for c_i in range(len(b.neighbors)):
					c = b.neighbors[c_i - c_i_off]
					if c == self.towns[0]:
						continue
					
					if c == a:
						continue
					
					if (a.x - c.x)**2 + (a.y - c.y)**2 < (b.x - c.x)**2 + (b.y - c.y)**2:
						del b.neighbors[c_i - c_i_off]
						b_i_off+=1
						for i in range(len(c.neighbors)):
							if c.neighbors[i] == b:
								del c.neighbors[i]
								c_i_off+=1
								break
						
						postman.connect_towns(a, c)
					
		# Build Routing tables so that all towns can know where they should forward mail.
		self.build_routing()
			
	# Build Routing tables so that all towns can know where they should forward mail.
	def build_routing(self):
		print("Building routing table...")
		
		for a in self.towns:
			self.routing[a.zip_code] = {}
			
			self.routing[a.zip_code][a.zip_code] = 0
			
			visited = []
			edge = [a]
			
			while len(edge) > 0:
				for n in edge[0].neighbors:
					if n in visited:
						continue
					
					self.routing[a.zip_code][n.zip_code] = self.routing[a.zip_code][edge[0].zip_code] + 1
					
					edge.append(n)
					
				visited.append(edge[0])
				del edge[0]
					
	
	# Outputs the world map as an image to the specified file
	def draw_map(self, fn):
		fnt = ImageFont.load_default()
		
		img = Image.new("RGB", (1920, 1080))
		drw = ImageDraw.Draw(img)
		for t in self.towns:
			for n in t.neighbors:
				drw.line((t.x + 960, t.y + 540, n.x + 960, n.y + 540), fill=(220, 220, 220))
			
		for t in self.towns:
			drw.ellipse((t.x-5 + 960, t.y-5 + 540, t.x+5 + 960, t.y+5 + 540), fill=(240, 240, 240))
			drw.text((t.x-5 + 960, t.y-15 + 540), t.get_address(), font=fnt, fill=(240, 240, 240))
		
		img.save(fn)
	
	# Connect two towns so that mail can be routed from one to the other directly.
	def connect_towns(a, b):
		a.neighbors.append(b)
		b.neighbors.append(a)
	
	# Gets the next available mail ID and increments it.
	def get_mail_ID(self):
		self.next_mail_ID = (self.next_mail_ID + 1) % 100000
		return self.next_mail_ID

# Represents a town, which has one post office, a zip code, and contains streets which contain houses which contain senders.
class town:
	# Initialize town. Constructor is passed the postman instance .
	def __init__(self, pm, pop_mul, x, y, player_ctrl):
		self.pm = pm
		
		# The town location
		self.x = x
		self.y = y
		
		# Whether this post office is controlled by a player.
		self.player_ctrl = player_ctrl
		
		# Population
		self.citizens = []
		
		# Post-office notifications. Neighboring post offices will send notifications about errors made.
		self.notes = []
		
		# Queue of mail for players to handle. Filled out by the mainloop for player-controlled POs
		self.player_queue = []
		
		# I was on the fence about including this on the town class. It keeps track of the amount of new mail in the player's queue during the generation of the mail that the player must handle.
		self.new_mail_in_pq = 0
		
		# Generate a random, unique zip code. For the purposes of building the routing table, it is vital that each town have a distinct zip code.
		do_gen_zip = True
		while do_gen_zip:
			self.zip_code = random.randint(10000, 99999)
			
			do_gen_zip = False
			for i in pm.towns:
				if self.zip_code == i.zip_code:
					do_gen_zip = True
					break
		
		# Get random town name from town name list
		self.name = random.choice(pm.town_names)
		
		# Initialize list for neighboring (connected) towns
		self.neighbors = []
		
		self.streets = []
		num_streets = max(2, round(random.gauss(5.5, 0.7) * (pm.settings.world_gen.town_size_mul*pop_mul)**(1/3)))
		for i in range(num_streets):
			self.streets.append(street(pm, pop_mul, self))
		
		# Sort streets alphabetically
		self.streets.sort(key = lambda a: a.name)
	
	# mail.handle() calls this function on towns which it detects have made a mistake. This adds the notification to a queue.
	def notify(self, notifier, text):
		self.notes.append((notifier, text))
		
	# Get the oldest note in the notes queue and remove it.
	def pop_note(self):
		n = self.notes[0]
		del self.notes[0]
		return n[0], n[1]
	
	# Display the town name, zip, and population, all streets, all houses, and all senders.
	def debug(self):
		print("Town of %s, %d, population %d:" % (self.name, self.zip_code, self.pop))
		for s in self.streets:
			print("  %s:" % s.name)
			for h in s.houses:
				print("    %d:" % h.number)
				for r in h.senders:
					print("      %s %s" % (r.first_name, r.last_name))
	
	def get_address(self):
		return self.name + ", " + str(self.zip_code)

# Represents a street, which contains houses which contain senders
class street:
	# Initialize street. Constructor is passed the postman instance.
	def __init__(self, pm, pop_mul, town):
		self.town = town
		
		# Get unique random street name from street name list
		do_gen_name = True
		while do_gen_name:
			self.name = random.choice(pm.street_names)
			
			do_gen_name = False
			for s in town.streets:
				if self.name == s.name:
					do_gen_name = True
					break
		
		self.houses = []
		num_houses = max(2, round(random.gauss(8, 1.3) * (pm.settings.world_gen.town_size_mul*pop_mul)**(1/3)))
		for i in range(num_houses):
			self.houses.append(house(pm, pop_mul, town, self))
		
		# Sort houses by numbers
		self.houses.sort(key = lambda a: a.number)
	
	def get_address(self):
		return self.name + "\n" + self.town.get_address()

# Represents a house, which contains senders. Each house has a small chance of being generated vacant.
class house:
	def __init__(self, pm, pop_mul, town, street):
		self.street = street
		
		# Get a unique random number for the street address
		do_gen_num = True
		while do_gen_num:
			self.number = random.randint(1, 55)
			
			do_gen_num = False
			for h in street.houses:
				if h.number == self.number:
					do_gen_num = True
					break
		
		self.senders = []
		if random.uniform(0, 1) > 0.05:
			num_senders = max(1, round(random.gauss(2, 0.3) * (pm.settings.world_gen.town_size_mul*pop_mul)**(1/3)))
			for i in range(num_senders):
				self.senders.append(sender(pm, pop_mul, town, self))
	
	def get_address(self):
		return str(self.number) + " " + self.street.get_address()
	
	# Houses ignore notifications
	def notify(self, notifier, text):
		pass

# Represents a sender
class sender:
	def __init__(self, pm, pop_mul, town, house):
		self.pm = pm
		self.town = town
		self.house = house
		
		# Update Citizenship
		town.citizens.append(self)
		pm.senders.append(self)
		
		# Initialize list to hold recent senders that mail has been received from.
		self.recv_from = []
		
		# Initialize list of mail from this sender that the sender believes to be in transit.
		self.in_transit = []
		
		self.first_name = random.choice(pm.first_names)
		self.last_name = random.choice(pm.last_names)
	
	# Gets this sender's address as a string.
	def get_address(self):
		return self.first_name + " " + self.last_name + "\n" + self.house.get_address()
	
	# Adds a piece of mail to this sender's list. The sender is notified 1-5 days after delivery that the mail is delivered, at which point it is removed.
	# If a sender has not been notified for a while, they are liable to submit requests to locate mail.
	def add_mail(self, mail):
		self.in_transit.append(mail)

# One instance of this class is held by each mail item. Its values are set by calling mail.handle and it describes what should be done to this piece of mail at the end of the day
# and if it has any errors.
class mail_action:
	def __init__(self):
		self.reset()
	
	def reset(self):
		# If this mail was routed in error.
		self.routing_error = False
		
		# If this mail was delivered to the wrong address.
		self.delivery_error = False
		
		# If this mail was delivered to a PO damaged.
		self.routed_damaged = False
		
		# If this mail was delivered damaged.
		self.delivered_damaged = False
		
		self.following = None

# Represents a piece of mail.
class mail:
	# Randomly creates a piece of mail from the sender to the recipient. is_story should be set to None if it is not story mail or to the name of the story mail item to send.
	def __init__(self, pm, sender, recipient, is_story):
		self.sender = sender
		self.recipient = recipient
		
		self.srce_zip = sender.town.zip_code
		self.dest_zip = recipient.town.zip_code
		
		self.ID = pm.get_mail_ID()
		
		self.srce = sender.get_address()
		self.dest = recipient.get_address()
		
		self.is_story = is_story
		
		self.act = mail_action()
		
		# Mail has a random chance of not having due postage
		if random.uniform(0, 1) < pm.srv.prob_sender_shortpays:
			if self.srce_zip != self.dest_zip and random.uniform(0, 1) < 0.5:
				self.stamp = 1
			else:
				self.stamp = 0
		elif self.srce_zip != self.dest_zip:
			self.stamp = 2
		else:
			self.stamp = 1
		
		# Some mail randomly generates with 1 level of damage
		if random.uniform(0, 1) < pm.srv.prob_sender_damages_mail:
			self.damage_lvl = 1
		else:
			self.damage_lvl = 0
			
		self.repair_lvl = 0
		
		# Whether this mail is handled automatically. If False, it is handled by a player.
		self.is_auto = True
		
		# Where the letter was last, where it is now, and where it will be on the next day.
		self.previous = sender.house
		self.current = sender.town
		
		# Tracks a piece of mail's age. Incremented by mail.advance()
		self.age = 0
	
	# Set self.act based on what should be done when advancing this mail.
	def handle(self):
		# Reset the action object.
		self.act.reset()
		
		# If mail is at a house...
		if type(self.current) is house:
			# Houses notify of damaged mail.
			if self.damage_lvl > self.repair_lvl:
				self.act.delivered_damaged = True
				
			# If mail is at the wrong house...
			if self.current != self.recipient.house:
				# Send to post office & notify
				self.act.following = self.current.street.town
				self.act.delivery_error = True
				return False
				
			# Otherwise, remove mail from the system. The sender will be notified immeediately by the magic of programming.
			else:
				self.sender.in_transit.remove(self)
				self.sender.pm.post.remove(self)
				return True
		
		# Otherwise, mail is at a town.
		else:
			# Routers repair mail and notify senders.
			if self.damage_lvl > self.repair_lvl:
				self.act.routed_damaged = True
			
			# Mail has a small chance of being damaged by the router.
			if random.uniform(0, 1) < self.sender.pm.srv.prob_router_damages_mail:
				self.damage()
			
			# If mail is in the town of the destination, forward it to the correct home
			if self.recipient.town.zip_code == self.current.zip_code:
				self.act.following = self.recipient.house
				return False
			
			# Otherwise, route mail towards its destination
			else:
				# Otherwise, route the mail in the correct direction. Loop over neighbors until one is found that is nearer to the destination.
				my_dis = self.sender.pm.routing[self.current.zip_code][self.recipient.town.zip_code]
				for n in self.current.neighbors:
					ne_dis = self.sender.pm.routing[n.zip_code][self.recipient.town.zip_code]
					if ne_dis < my_dis:
						self.act.following = n
						
						# If mail should be routed to the place that routed it to this PO, notify that the mail was sent to this PO in error.
						if self.previous == self.act.following:
							self.act.routing_error = True
						
						return False
				
			print("Could not route " + self.get_details())
			return False
	
	# Move this mail-item towards its destination.
	def advance(self):
		if self.act.following is None:
			print("Fatal, MI not routed: " + self.get_details())
		
		if self.act.delivery_error:
			self.current.street.town.notify(self.current, "Mail routed to incorrect residence.")
		
		if self.act.routing_error:
			self.act.following.notify(self.current, "Mail Routed in Error.")
		
		if self.act.delivered_damaged:
			self.previous.notify(self.current, "Mail arrived to residence damaged.")
		
		if self.act.routed_damaged:
			self.previous.notify(self.current, "Mail arrived to PO damaged.")
			self.repair()
			
		self.previous = self.current
		self.current = self.act.following
		
		self.age += 1
	
	# Increment the damage value of this mail, up to a maximum of 3.
	def damage(self):
		if self.damage_lvl < 3:
			self.damage_lvl += 1
	
	# Increment the repair value of this mail, up to the current damage value.
	def repair(self):
		if self.repair_lvl < self.damage_lvl:
			self.repair_lvl += 1
	
	# Gets a string representing this piece of mail
	def get_details(self):
		return "#%05d | %s -> %s | %d/%d | %d" % (self.ID, self.srce.replace("\n", ", "), self.dest.replace("\n", ", "), self.damage_lvl, self.repair_lvl, self.stamp)