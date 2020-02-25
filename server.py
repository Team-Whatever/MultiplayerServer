import random
import socket
import time
from _thread import *
import threading
from datetime import datetime
import json
import ast

clients_lock = threading.Lock()
connected = 0
teamId = 0

maxHealth = 100
numUpdatePerSeconds = 10
clients = {}

def connectionLoop(sock):
   global teamId
   global maxHealth
   while True:
      data, addr = sock.recvfrom(1024)
      data = ast.literal_eval(data.decode('utf-8'))
      
      if addr in clients:
         # existing user
         clients[addr]['lastBeat'] = datetime.now()
         if 'command' in data and data['command'] != '':
            print( "received from client " + str(addr) + " : " + data['command'] )
            clients[addr]['command'].append( data['command'] )
         if 'pos' in data:
             clients[addr]['pos'] = data['pos']
         if 'rotation' in data:
            clients[addr]['rotation'] = data['rotation']
         if 'health' in data:
            clients[addr]['health'] = data['health']
         #print(str(addr) + " : " + str(data))
      else:
         # new user
         if 'message' in data and data['message'] == 'connect':
            clients[addr] = {}
            clients[addr]['id'] = addr
            unitId = random.randint( 0, 10 )
            clients[addr]['unitId'] = unitId
            clients[addr]['teamId'] = teamId
            teamId += 1
            pos = { "x" : random.uniform( 0.0, 5.0 ), "y": 0, "z": random.uniform( 0.0, 5.0 ) }
            clients[addr]['pos'] = pos
            clients[addr]['rotation'] = { "x" : 0, "y": 0, "z": 0, "w": 0 }
            clients[addr]['health'] = maxHealth
            clients[addr]['lastBeat'] = datetime.now()
            clients[addr]['command'] = []
            
            for c in clients:
               if c is addr:
                  # new user connected
                  sendPlayerInfo( sock, addr, clients[addr], 0, c )
               else:
                  # send new client joined to the existing users
                  sendPlayerInfo( sock, addr, clients[addr], 1, c )
               
            # TODO : send all players information at once
            # send all the data of connected clients to the newly connected client 
            for c in clients:
               # send existing users to the newly connected user
               if c is not addr:
                  sendPlayerInfo( sock, c, clients[c], 1, addr )


def sendPlayerInfo( sock, sender, player, command, receiver):
   message = {"cmd": command, "player":{"id":str(sender), "unitId" : player['unitId'], "teamId" : player['teamId'], "pos":player['pos'], "health":player['health']}}
   m = json.dumps(message)
   sock.sendto( bytes(m,'utf8'), (receiver[0], receiver[1]) )


def cleanClients(sock):
   while True:
      for c in list(clients.keys()):
         if (datetime.now() - clients[c]['lastBeat']).total_seconds() > 10:
            print('Dropped Client: ', c)
            clients_lock.acquire()
            del clients[c]
            clients_lock.release()
            message = {"cmd": 3, "player":{"id":str(c)}}
            m = json.dumps(message)
            for c in clients:
               sock.sendto(bytes(m,'utf8'), (c[0],c[1]))
      time.sleep(1)


def gameLoop(sock):
   while True:
      GameState = {"cmd": 2, "players": []}
      clients_lock.acquire()
      
      for c in clients:
         player = {}
         player['id'] = str(c)
         player['pos'] = clients[c]['pos']
         player['unitId'] = clients[c]['unitId']
         player['teamId'] = clients[c]['teamId']
         player['rotation'] = clients[c]['rotation']
         player['health'] = clients[c]['health']
         if 'command' in clients[c] and len(clients[c]['command']) > 0:
            command = clients[c]['command'].pop(0)
            print( "send to client " + str(c) + " : " + command )
            player['command'] = command
         GameState['players'].append(player)
      s=json.dumps(GameState)
      #print("game: ", s)
      for c in clients:
         #print("client: ", str(c[0]), str(c[1]))
         sock.sendto(bytes(s,'utf8'), (c[0],c[1]))
      clients_lock.release()
      time.sleep(1.0/numUpdatePerSeconds)


def main():
   port = 12345
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.bind(('', port))
   start_new_thread(gameLoop, (s,))
   start_new_thread(connectionLoop, (s,))
   start_new_thread(cleanClients,(s,))
   while True:
      time.sleep(1)

if __name__ == '__main__':
    main()
