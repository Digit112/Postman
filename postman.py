import math
import random
import threading

from classes import *
	
pm = postman()

pm.gen_map()
pm.draw_map("map.png")

# This function takes a mail item and adds it to the appropriate player's queue or ignores it as needed.
def add_mail_to_pq(m):
	# If this mail item is in a player-controlled town...
	if m.current.player_ctrl:
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
	

while True:
	# Get all mail for the players to handle for each player-controlled PO
	# Shuffle the mail to prevent bias in what ends up in the player's queue.
	random.shuffle(m.post)
	
	# Reset the new_mail_in_pq for each town
	for t in pm.towns:
		t.new_mail_in_pq = 0
		
	# Move all mail to player queues as needed
	for m in pm.post:
		add_mail_to_pq(m)
	
	# Loop over towns. If the mail queues aren't met, generate new mail randomly.
	for t in pm.towns:
		if t.player_ctrl:
			while len(t.player_queue) < pm.day.mail_limit and t.new_mail_in_pq < pm.day.new_mail_quota and len(t.player_queue) < pm.day.mail_quota:
				pm.gen_mail()
				add_mail_to_pq(pm.post[-1])
	
	# At this point, all players have queues meeting the mail quota and the mail limit (unless story mail pushed it over), and hopefully meeting the new mail quota. All remaining mail will be handled automatically.