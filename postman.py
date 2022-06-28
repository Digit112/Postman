import math
import random
import threading
import time

from postman_classes import *
from interface import *
	
pm = postman("postman_singleplayer")

pm.gen_map()
pm.draw_map("map.png")

# This function takes a mail item and adds it to the appropriate player's queue or ignores it as needed.
def add_mail_to_pq(m):
	# If this mail item is in a player-controlled town...
	if type(m.current) == town and m.current.player_ctrl:
		# If this is a story item, move it to the player's queue.
		if m.is_story:	
			m.current.player_queue.append(m)
			m.is_auto = False
			return
		
		# If the mail limit is not met...
		if len(m.current.player_queue) < pm.day.mail_limit:
			# If this mail is new and the new mail quota is not met, add it to the player's queue
			if m.age == 0 and m.current.new_mail_in_pq < pm.day.new_mail_quota:
				m.current.player_queue.append(m)
				m.current.new_mail_in_pq += 1
				m.is_auto = False
				return
			
			# If the mail quota is not met, add it to the player's queue.
			if len(m.current.player_queue) < pm.day.mail_quota:
				m.current.player_queue.append(m)
				m.is_auto = False
				return

if pm.config.mode == "singleplayer":
	# Create local client
	cli = pm_cli(True, pm, None)
	
	# Start handling player input
	cli_thr = threading.Thread(target=pm_cli.mainloop, args=(cli, False))
	cli_thr.start()

	# Start the mail simulation.
	while True:
		# Handle mail
		for t in pm.towns:
			# Handle mail left in the player queues from the previous day.
			if t.player_ctrl:
				num_unhandled = 0
				
				for m in t.player_queue:
					if m.following is None:
						m.handle()
						num_unhandled += 1
				
				t.notify(t, "There were " + str(num_unhandled) + " mail items left in your queue at the end of the day yesterday.")
		
		# Handle all automated mail
		m_i = 0
		while m_i < len(pm.post):
			m = pm.post[m_i]
			
			is_destroyed = False
			if type(m.current) is house or not m.current.player_ctrl:
				is_destroyed = m.handle()
			
			if not is_destroyed:
				m_i += 1
		
		# Handle remaining mail. This is mail in a player-controlled post office that didn't end up in the queue.
		m_i = 0
		while m_i < len(pm.post):
			m = pm.post[m_i]
			
			is_destroyed = False
			if m.current.player_ctrl and m not in m.current.player_queue:
				is_destroyed = m.handle()
			
			if not is_destroyed:
				m_i += 1
		
		# Reset player queues
		for t in pm.towns:
			if t.player_ctrl:
				t.player_queue = []
		
		# Move all mail to its destination
		for m in pm.post:
			m.advance()
		
		# Get all mail for the players to handle for each player-controlled PO
		# Shuffle the mail to prevent bias in what ends up in the player's queue.
		#random.shuffle(pm.post)
		
		# Reset the new_mail_in_pq for each town
		for t in pm.towns:
			t.new_mail_in_pq = 0
			
		# Move all mail to player queues as needed
		for m in pm.post:
			add_mail_to_pq(m)
		
		# Loop over towns. If the mail quotas aren't met, generate new mail randomly.
		for t in pm.towns:
			if t.player_ctrl:
				while len(t.player_queue) < pm.day.mail_limit and t.new_mail_in_pq < pm.day.new_mail_quota or len(t.player_queue) < pm.day.mail_quota:
					pm.gen_mail()
					add_mail_to_pq(pm.post[-1])
		
		# At this point, all players have queues meeting the mail quota and the mail limit (unless story mail pushed it over), and hopefully meeting the new mail quota. All remaining mail will be handled automatically.
		
		# Set is_simulating to false and wait for the player to update this by ending the day.
		pm.is_simulating = False
		while not pm.is_simulating:
			time.sleep(0.1)
			pass
		
elif pm.config.mode == "multiplayer":
	print("multiplayer not implemented")
	exit()