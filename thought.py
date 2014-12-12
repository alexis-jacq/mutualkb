#!/usr/bin/python           

# dynamic world learning & infering server

import logging; logger = logging.getLogger('mylog');

import socket
import random     
import threading
import time  
import numpy
import sqlite3
import Queue

#from processkb import DEFAULT_MODEL
from kb import TABLENAME, KBNAME


requests = Queue.Queue()
sock = socket.socket()         
port = 12340           
sock.bind(("", port))        

sock.listen(5)     

THOUGHT_RATE = 2 #Hz <-- ~ reaction time
FIRE_TIME = 3 #s
END = False
DEFAULT_MODEL = 'K_myself'
THRESHOLD = 0.

class Dynamic:
    def __init__(self):
        self.events = {'':{'':0}}
        self.current_event = ''      # empty event
        
    def update(self, kb, nodes):

        for node_id,matter in nodes:
            print('%s with matter %f' % (node_id, matter))
            
            fire_time = 3 #0.5*matter*FIRE_TIME/THRESHOLD
            next_event = node_id
            
            if next_event in self.events[self.current_event]:
                self.events[self.current_event][next_event] += 1 + random.random()/100
            else:
                if next_event in self.events:
                    self.events[self.current_event][next_event] = 1 + random.random()/100
                else:   
                    self.events[self.current_event][next_event] = 1 + random.random()/100
                    self.events[next_event] = {next_event:0}
            fire(kb, next_event, fire_time)
        
        next_event = max(thought.events[thought.current_event],key = thought.events[thought.current_event].get)
        self.current_event = next_event
    

thought = Dynamic()  

def counts(kb):
    global thought
    
    while not END:
        
        douse(kb)
        
        '''check si new event'''
        nodes = get_attractive_nodes(kb)
        ''' si new event --> update'''
        if nodes:
            thought.update(kb, nodes)
            
        else:
            next_event = max(thought.events[thought.current_event],key = thought.events[thought.current_event].get)
            if next_event:
                thought.events[thought.current_event][next_event] += random.random()/100
                thought.current_event = next_event
                time.sleep(1)
                logger.info('current event = %s' % thought.current_event)
                fire(kb, next_event, FIRE_TIME)
        
        clock(kb)
        
        
# KB-THINKING methods
#----------------------------

def get_attractive_nodes(kb):
     nodes = {(row[0], row[1]) for row in kb.conn.execute('''SELECT id, matter FROM %s WHERE matter>%f''' %(TABLENAME, THRESHOLD))}
     return nodes

def fire(kb, node_id, fire_time):
    '''this methode actives the selected nodes'''
    kb.wait_turn()
    
    kb.conn.execute('''UPDATE %s SET active = %i WHERE id=?''' % (TABLENAME, fire_time), (node_id,))
    kb.conn.commit()
    #time.sleep(1/THOUGHT_RATE)

def clock(kb):
    ''' update the time each node keeps firing '''
    kb.wait_turn()
    kb.conn.execute('''UPDATE %s SET active = (SELECT active)-1 WHERE active>0''' % TABLENAME)
    kb.conn.commit()

def douse(kb):
    '''this methode disactives the time-out nodes '''
    kb.wait_turn()
    kb.conn.execute('''UPDATE %s SET matter=0 WHERE active>0.1 ''' % TABLENAME)
    kb.conn.commit()


def kill(kb, node_id):
    '''this methode removes the selected nodes '''
    kb.wait_turn()
    kb.conn.execute('''DELETE FROM %s WHERE id=?''' % TABLENAME, (node_id,))
    kb.conn.commit()
        

def thought_start(kb):
    global END
    END = False
    
    print('starting...')
    counts(kb)
    print('ok !')

def thought_stop():
    global END
    END = True

