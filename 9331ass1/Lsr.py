#coding: utf-8
import threading
import queue
import json
from socket import *
import time
import sys

def readfile(filename):
	global my_ID
	global my_port
	global graph
	global state_packet
	with open(filename) as f:
		filelines = f.readlines()
	nb=dict()
	try:
		for lines in filelines:
			line = lines.strip().split(' ')
			#print(len(line))
			#print(line)
			if (len(line) == 2):
				my_ID = line[0]
				my_port = int(line[1])
			if (len(line) > 2):
				nb[line[0]] =(line[1],line[2])
				state_packet[my_ID] = nb
				graph[my_ID] = nb
		return nb
	except (ValueError):
		print("config wrong!")
		exit(0)

def listen():
	global graph
	global restrict_dict
	while True:
		message,clientAddress = my_socket.recvfrom(2048)
		data_list = json.loads(message.decode('ascii'))
		if data_list[0] != 1:
			if data_list[1] in restrict_dict:
				if restrict_dict[data_list[1]] >= data_list[2]:
					continue
			restrict_dict[data_list[1]] = data_list[2]
		#implement restricting link-state boardcasts
		
		accept_queue.put([data_list,clientAddress])

def broadcast():
	T = time.time()
	for key in Neighbour_dict:
		sending_queue.put([[0,my_ID,T,state_packet],int(Neighbour_dict[key][1])])
	time.sleep (UPDATE_TIME)
	

	while True:
		T = time.time()
		for key in Neighbour_dict:
			sending_queue.put([[0,my_ID,T,state_packet],int(Neighbour_dict[key][1])])
		time.sleep(UPDATE_TIME)

def Dijkstra():
	while 1:
		time.sleep(ROUTE_UPDATE_INTERVAL)
		s={}
		s[my_ID]=0
		u={}
		print(f"I am Router {my_ID}")
		for key in graph:
			if key != my_ID:
				u[key] =[key,float('inf')]
		for key in Neighbour_dict:
			if key in u:
				u[key] = [key,float(Neighbour_dict[key][0])]
		while len(u) != 0:
			minID= min(u, key=lambda k:u[k][1])
			#print(minID)
			s[minID] = u[minID]
			u.pop(minID)
			for key in graph[minID]:
				if (key in u) and (key != my_ID) :
					if (float(graph[minID][key][0]) + s[minID][1]) < u[key][1]:
						u[key][0] = s[minID][0]+key
						u[key][1] = round(float(graph[minID][key][0]) + s[minID][1],2)
		
		for i in sorted(s):
			if i != my_ID:
				print(f"Least cost path to router {i}:{my_ID + s[i][0]} and the cost is {s[i][1]}")

def main_thread():
	global heartbeats_dict
	while True:
		acpt= accept_queue.get()
		Type,messageID,Time,datapath,sendport = \
			acpt[0][0],acpt[0][1],acpt[0][2],acpt[0][3],acpt[1]
		#broadcast type0
		#node dead type1
		#
		if Type == 0:
			with lock:
				heartbeats_dict[messageID] = 0

		if Type == 1:
			with lock:
				if datapath in graph:
					del graph[datapath]

		if Type != 1:
			for key in datapath:
				graph[key]=datapath[key]          #update network topology

		for key in Neighbour_dict:
			nb_port = int(Neighbour_dict[key][1])
			if nb_port == sendport:
				continue
			if key == messageID:
				continue
			if Type == 1:
				sending_queue.put([[1,messageID,Time,datapath],nb_port])
			else:
				sending_queue.put([[2,messageID,Time,datapath],nb_port])


def checkalive():
	while True:
		off_time=time.time()
		with lock:
			for key in Neighbour_dict:
				if  key not in heartbeats_dict:
					heartbeats_dict[key] = 0
				else:
					if key in graph:
						if heartbeats_dict[key] >= 3:
							del graph[key]
							for keyy in Neighbour_dict:
								if keyy != key:
									nb_port=int(Neighbour_dict[keyy][1])
									sending_queue.put([[1,my_ID,off_time,key],nb_port])
						else:
							heartbeats_dict[key] = heartbeats_dict[key] + 1
		time.sleep(UPDATE_TIME)

def sending():
	while True :
		s=sending_queue.get()
		send(s[0], s[1])


def send(data,port):
	config = json.dumps(data)
	my_socket.sendto(
		bytes(
			config, 
			encoding = 'ascii'
		),
		('127.0.0.1',port)
	)


# +-----------------------------------+
# | TYPE | ID | TIMESTAMP | DATA | Port
# +-----------------------------------+
UPDATE_TIME = 1
ROUTE_UPDATE_INTERVAL = 30

my_port = 0
my_ID = ""

state_packet = {}
graph = {}
link_state_packet=[]
restrict_dict = {}
heartbeats_dict= {}
Neighbour_dict = readfile(sys.argv[1])

my_socket = socket(AF_INET,SOCK_DGRAM)
my_socket.bind(('127.0.0.1',my_port))

accept_queue=queue.Queue()
sending_queue=queue.Queue()
lock=threading.Lock()

T1 = threading.Thread(target=listen)
T2 = threading.Thread(target=broadcast)
T3 = threading.Thread(target=main_thread)
T4 = threading.Thread(target=sending)
T5 = threading.Thread(target=checkalive)
T6 = threading.Thread(target=Dijkstra)

T1.start()
T2.start()
T3.start()
T4.start()
T5.start()
T6.start()

