import math
import random
import json
from types import SimpleNamespace

from PIL import Image, ImageDraw

# Function that reads a json file and returns an object representing the data
def load_json(fn):
	fin = open(fn, "r")
	x = json.loads(fin.read(), object_hook=lambda d: SimpleNamespace(**d))
	fin.close()
	return x

# This class tracks the gamestate, including a list of all senders, the post network shape, and all mail in transit.
class postman:
	# The postman initializer creates the game map and all the senders.
	def __init__(self):
		# Load settings
		self.settings = load_json("settings.json")
		
		# Load list of days (rulesets)
		self.days = load_json("days.json")
		
		# Set default day
		self.day = self.days.standard

		# Load localization file
		self.strings = load_json("localization/" + self.settings.language + ".json")
		
		# Load town name list
		fin = open("names/town_names.txt", "r")
		self.town_names = fin.read().split("\n")
		fin.close()
		
		# Load street name list
		fin = open("names/street_names.txt", "r")
		self.street_names = fin.read().split("\n")
		fin.close()
		
		# Load first name list
		fin = open("names/first_names.txt", "r")
		self.first_names = fin.read().split("\n")
		fin.close()
		
		# Load last name list
		fin = open("names/last_names.txt", "r")
		self.last_names = fin.read().split("\n")
		fin.close()
		
		# Initialize list of all senders in the game
		self.senders = []
		
		# Initialize list for all mail in transit
		self.post = []
		
		# Initialize list of towns
		self.towns = []
	
	# Generates a town. pop_mul is a multiplier for the average population. Actual population varies a lot.
	# Towns of pop_mul 1 will have an average population of 80.
	def add_town(self, pop_mul, x, y):
		return town(self, pop_mul, x, y)
	
	# Generates the game world according to the settings. Towns must be at least 50
	def gen_map(self):
		# Generate the player's town
		self.towns.append(self.add_town(0.5, 0, 0))
		
		# Generate connecting towns
		for i in range(0, self.settings.world_gen.nct):
			# Town size is based on which town is being generated
			t_size = 0.5
			if i == 1:
				t_size = 1.8
			elif i == 2:
				t_size = 0.8
			
			# Continuously generate coordinates until either minimum town separation is satisfied or the number of tries is exhausted.
			# If a town exhausts all attempts, stop generating connecting towns.
			gen_successful = False
			for j in range(200):
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
				self.towns.append(self.add_town(t_size, x, y))
				postman.connect_towns(self.towns[0], self.towns[-1])
			else:
				break
		
		# Generate additional towns
		for i in range(0, self.settings.world_gen.nat):
			# Continuously generate coordinates until either minimum town separation is satisfied or the number of tries is exhausted.
			# If a town exhausts all attempts, stop generating connecting towns.
			gen_successful = False
			for j in range(200):
				angle = random.uniform(0, 2*math.pi)
				radius = random.uniform(280, 940)
				
				x = radius * math.cos(radius)
				y = radius * math.sin(radius)
				
				if y < -520 or y > 520:
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
				self.towns.append(self.add_town(t_size, x, y))
				postman.connect_towns(min_town, self.towns[-1])
			else:
				break
	
	# Outputs the world map as an image to the specified file
	def draw_map(self, fn):
		img = Image.new("RGB", (1920, 1080))
		drw = ImageDraw.Draw(img)
		for t in self.towns:
			drw.ellipse((t.x-5 + 960, t.y-5 + 540, t.x+5 + 960, t.y+5 + 540), fill=(240, 240, 240))
			
			for n in t.neighbors:
				drw.line((t.x + 960, t.y + 540, n.x + 960, n.y + 540), fill=(220, 220, 220))
		
		img.save(fn)
	
	# Connect two towns so that mail can be routed from one to the other directly.
	def connect_towns(a, b):
		a.neighbors.append(b)
		b.neighbors.append(a)

# Represents a town, which has one post office, a zip code, and contains streets which contain houses which contain senders.
class town:
	# Initialize town. Constructor is passed the postman instance .
	def __init__(self, pm, pop_mul, x, y):
		self.pm = pm
		
		self.x = x
		self.y = y
		
		# Population
		self.citizens = []
		
		# Generate random zip code
		self.zip_code = random.randint(10101, 99090)
		
		# Get random town name from town name list
		self.name = random.choice(pm.town_names)
		
		# Initialize list for neighboring (connected) towns
		self.neighbors = []
		
		self.streets = []
		num_streets = max(2, round(random.gauss(5.5, 0.7) * (pm.settings.world_gen.tsm*pop_mul)**(1/3)))
		for i in range(num_streets):
			self.streets.append(street(pm, pop_mul, self))
	
	# Display the town name, zip, and population, all streets, all houses, and all senders.
	def debug(self):
		print("Town of %s, %d, population %d:" % (self.name, self.zip_code, self.pop))
		for s in self.streets:
			print("  %s:" % s.name)
			for h in s.houses:
				print("    %d:" % h.number)
				for r in h.senders:
					print("      %s %s" % (r.first_name, r.last_name))

# Represents a street, which contains houses which contain senders
class street:
	# Initialize street. Constructor is passed the postman instance.
	def __init__(self, pm, pop_mul, town):
		self.town = town
		
		# Get random street name from street name list
		self.name = random.choice(pm.street_names)
		
		self.houses = []
		num_houses = max(2, round(random.gauss(8, 1.3) * (pm.settings.world_gen.tsm*pop_mul)**(1/3)))
		for i in range(num_houses):
			self.houses.append(house(pm, pop_mul, town, self))

# Represents a house, which contains senders. Each house has a small chance of being generated vacant.
class house:
	def __init__(self, pm, pop_mul, town, street):
		self.street = street
		
		# Get a random number for the street address
		self.number = random.randint(1, 55)
		
		self.senders = []
		if random.uniform(0, 1) > 0.05:
			num_senders = max(1, round(random.gauss(2, 0.3) * (pm.settings.world_gen.tsm*pop_mul)**(1/3)))
			for i in range(num_senders):
				self.senders.append(sender(pm, pop_mul, town, self))

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
		
		self.first_name = random.choice(pm.first_names)
		self.last_name = random.choice(pm.last_names)
	
	# Gets this sender's address as a string.
	def get_address(self):
		return "%s %s\n%d %s\n%s\n%d" % (self.first_name, self.last_name, self.house.number, self.house.street.name, self.house.street.town.name, self.house.street.town.zip_code)
	
	# Generates a new mail item.
	def gen_mail(self):
		recipient = None
		
		# Mail has a chance to be in reply to an individual from whom mail was recently received
		if random.uniform() < 0.5 and len(self.recv_from) > 0:
			recipient = random.choice(self.recv_from)
		
		# Mail has a good chance of being addressed to someone within the sender's town
		elif random.uniform() < 0.6:
			while True:
				recipient = random.choice(self.town.citizens)
				
				# Ensure the recipient is not the sender
				if recipient != sender:
					break
					
				print("sender is recipient (1)")
		
		# If both previous conditions failed, just pick a random person anywhere.
		else:
			while True:
				recipient = random.choice(self.town.citizens)
				
				# Ensure the recipient is not the sender
				if recipient != sender:
					break
					
				print("sender is recipient (2)")
		
		pm.post.append(mail(pm, self, recipient))
			
	
# Represents a piece of mail. "send" and "dest" are addresses returned by sender.get_address()
class mail:
	def __init__(self, pm, sender, recipient):
		self.sender = sender
		self.recipient = recipient
		
		self.srce = sender.get_address()
		self.dest = recipient.get_address()