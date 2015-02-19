#!/usr/bin/python

# learning & infering in a dynamic world encoded as nodes in a knowledge-database

import logging; logger = logging.getLogger('mylog');

import threading
import time
import random
import kb
import operator

THOUGHT_RATE = 2 #Hz <-- ~ reaction time
FIRE_TIME = 3 #s
END = False
THRESHOLD = 0.


def cmp(c1, c2):
    a,b = c1
    c,d = c2
    s = b+d
    r = random.uniform(0,s)
    return 1 if r>b else -1


def random_pull(distribution): # dist. is a list of coulpes
    if distribution :
        sorted_couples = sorted(distribution,cmp)
        return sorted_couples[0][0]
    else:
        return None


class Dynamic:
    def __init__(self):
        self.events = {'':{'':0}}
        self.think = '' # empty event

    def update(self, kb, nodes):

        for node_id, matter in nodes:
            print '%s with matter %f' % (node_id, matter)
            #logger.info('%s with matter %f' % (node_id, matter))

            fire_time = 3 #0.5*matter*FIRE_TIME/THRESHOLD
            next_event = node_id

            if next_event not in self.events:
                self.events[next_event] = {next_event: 0*random.random()/100}

            current_events = kb.get_actives_nodes()

            if current_events:

                for current_event, level in current_events:

                    if current_event not in self.events:
                        self.events[current_event] = {current_event: 0*random.random()/100}

                    if next_event in self.events[current_event]:
                        self.events[current_event][next_event] += 1 + level/FIRE_TIME + random.random()/100
                    else:
                        self.events[current_event][next_event] = 1 + level/FIRE_TIME + random.random()/100

                    if current_event in self.events[next_event]:
                        self.events[next_event][current_event] += random.random()/100
                    else:
                        self.events[next_event][current_event] = random.random()/100

            kb.fire(next_event, fire_time)


        if self.think:
            # deterministic :
            #next_think = max(self.events[self.think],key = self.events[self.think].get)

            # random :
            distribution = self.events[self.think].items()
            next_think = random_pull(distribution)
            self.think = next_think
            kb.fire(self.think, FIRE_TIME)
        else:
            self.think = next_event
            kb.fire(self.think, FIRE_TIME)


dynamic = Dynamic()

def counts(kb):
    global dynamic

    while not END:

        kb.douse()

        '''check si new event'''
        nodes = kb.get_attractive_nodes(THRESHOLD)
        ''' si new event --> update'''
        if nodes:
            dynamic.update(kb, nodes)
            #show_dynamic()

        else:
            # deterministic :
            #next_think = max(dynamic.events[dynamic.think],key = dynamic.events[dynamic.think].get)

            # random :
            distribution = dynamic.events[dynamic.think].items()
            next_think = random_pull(distribution)
            if next_think:
                dynamic.events[dynamic.think][next_think] += abs(random.random()/100)
                dynamic.think = next_think
                time.sleep(1)
                logger.info('current event = %s' % dynamic.think)
                kb.fire(next_think, FIRE_TIME)

        kb.clock()

def show_dynamic():
    print dynamic.events

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
    #show_dynamic()
