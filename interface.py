

# This file implements the interface between the server (simulation) and client (player interface)
class pm_cli:
	def __init__(self, pm, addr):
		self.pm = pm
		self.player_town = pm.towns[0]
	
	# Handle player input on a loop. This should be called in a seperate thread. Thread locks are used to prevent race conditions.
	# If use_gui, load and handle input via the gui interface. Otherwise, use the command line interface
	def mainloop(self, use_gui):
		# Create data structure to contain the boxes the player can put mail in.
		boxes = {}
		
		# Allow player to place mail in recovery.
		boxes["recovery"] = []
		
		# Allow player to route mail to adjacent towns.
		for n in self.player_town.neighbors:
			boxes[str(n.zip_code)] = []
		
		# Allow player to route mail to each house in their town.
		for s in self.player_town.streets:
			for h in s.houses:
				boxes[(str(h.number) + " " + s.name).lower()] = []
		
		# Create map for converting names to objects in memory.
		get_place_by_name = {}
		get_place_by_name["recovery"] = "recovery"
		
		for n in self.player_town.neighbors:
			get_place_by_name[str(n.zip_code)] = n
			
		for s in self.player_town.streets:
			for h in s.houses:
				get_place_by_name[(str(h.number) + " " + s.name).lower()] = h
		
		# Begin checking for player input
		if use_gui:
			print("GUI not yet implemented.")
			exit()
		else:
			while True:
				# Wait for the server to stop simulating
				while self.pm.is_simulating:
					pass
				
				# Display notifications.
				print("Notifications from yesterday:")
				while len(self.player_town.notes) != 0:
					print(self.player_town.notes[0][0].get_address().replace("\n", " ") + ": " + self.player_town.notes[0][1])
					del self.player_town.notes[0]
				
				# Take input on a loop.
				while True:
					inp = input("> ").lower().split(" ")
					
					# Help page
					if inp[0] == "help" or inp[0] == "?":
						if len(inp) < 2:
							print("Display this help page or the help page for a specific command:\n(help | h | ?) [<command>]\n")
							print("Get all mail in brief:\n(get_all_mail | gam)\n")
							print("Get details of a mail item by its position in your queue:\n(get_mail_item | gmi) <position>\n")
							print("Get locations mail can be routed to:\n(get_routables | grs)\n")
							print("Repair Mail:\n(repair | rpr) <position>\n")
							print("Route mail:\n(route | rte) <mail_position> <destination>\n")
							print("End the day:\n(end_day | end)\n")
					
					# Get all mail in the player's queue
					elif inp[0] == "get_all_mail" or inp[0] == "gam":
						for m_i in range(len(self.player_town.player_queue)):
							m = self.player_town.player_queue[m_i]
							print(str(m_i) + ", " + ("Unrouted" if m.act.following is None else "  Routed") + ": " + m.get_details())
					
					# Get the details of a mail item
					elif inp[0] == "get_mail_item" or inp[0] == "gmi":
						if len(inp) < 2:
							print("invalid command")
							continue
						try:
							m_i = int(inp[1])
						except ValueError:
							print("invalid command")
							continue
						
						m = self.player_town.player_queue[m_i]
						print(str(m_i) + ": " + m.srce.replace("\n", ", ") + " -> " + m.dest.replace("\n", ", "))
						print("damage: " + str(m.damage_lvl) + ", repair: " + str(m.repair_lvl) + ", postage: " + str(m.stamp))
						print("Mail's previous location: " + m.previous.get_address().replace("\n", ", "))
						print("Mail's next location: " + ("Not yet specified" if m.act.following is None else m.act.following.get_address().replace("\n", ", ")))
					
					# List all available locations that can be routed to
					elif inp[0] == "get_routables" or inp[0] == "grs":
						print("recovery")
						for n in self.player_town.neighbors:
							print(n.zip_code)
						for s in self.player_town.streets:
							for h in s.houses:
								print(str(h.number) + " " + s.name)
					
					# Repair mail
					elif inp[0] == "repair" or inp[0] == "rpr":
						if len(inp) < 2:
							print("Invalid command, not enough arguments.")
							continue
							
						try:
							inp[1] = int(inp[1])
						except ValueError:
							print("Invlid command, first parameter should be a number.")
						
						self.player_town.player_queue[inp[1]].repair()
					
					# Route mail
					elif inp[0] == "route" or inp[0] == "rte":
						try:
							inp[1] = int(inp[1])
						except ValueError:
							print("Invalid mail posiition. Must be a number.")
							continue
						
						for i in range(3, len(inp)):
							inp[2] = inp[2] + " " + inp[i]
						
						try:
							# Put mail in the specified box
							boxes[inp[2]].append(self.player_town.player_queue[inp[1]])
							
							# Set the mail item's next location
							self.player_town.player_queue[inp[1]].act.following = get_place_by_name[inp[2]]
						except KeyError:
							print("Location " + inp[2] + " specified does not exist.")
							continue
					
					# End the day.
					elif inp[0] == "end_day" or inp[0] == "end":
						self.pm.is_simulating = True
						break