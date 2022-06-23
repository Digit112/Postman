import random
import threading
import time

def handle_list_items(l, mod, off):
	for i in range(off, len(l), mod):
		print(off, l[i])

l = []
for i in range(40):
	l.append(i)

mod = 3

thr = []
for i in range(mod):
	thr.append(threading.Thread(target=handle_list_items, args=(l, mod, i)))
	thr[-1].start()