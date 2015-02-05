#!/usr/bin/python

# learning & infering in a dynamic world encoded as nodes in a knowledge-database

import logging; logger = logging.getLogger('mylog');

import threading
import time
import numpy
import sqlite3
import Queue
import random
import kb


THOUGHT_RATE = 2 #Hz <-- ~ reaction time
FIRE_TIME = 3 #s
END = False
THRESHOLD = 0.


class Dynamic:
    def __init__(self):
        self.events = {'':{'':0}}
        self.current_event = ''      # empty event

    def update(self, kb, nodes):

        for node_id, matter in nodes:
            print '%s with matter %f' % (node_id, matter)

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
            kb.fire(next_event, fire_time)

        next_event = max(thought.events[thought.current_event],key = thought.events[thought.current_event].get)
        self.current_event = next_event


thought = Dynamic()

def counts(kb):
    global thought

    while not END:

        kb.douse()

        '''check si new event'''
        nodes = kb.get_attractive_nodes(THRESHOLD)
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
                kb.fire(next_event, FIRE_TIME)

        kb.clock()


# threading funtions :
#=====================

def thought_start(kb):
    global END
    END = False

    print('starting...')
    counts(kb)
    print('ok !')

def thought_stop():
    global END
    END = True
