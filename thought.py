#!/usr/bin/python           

# dynamic world learning & infering server

import logging; logger = logging.getLogger("minimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import socket
import random     
import threading
import time  
import numpy

sock = socket.socket()         
port = 12345           
sock.bind(("", port))        

sock.listen(5)     

end = 0


class Dynamic:
    def __init__(self):
        self.events = {'':{'':0}}
        self.current_event = ''      # empty event
        
    def update(self, next_event):
        if next_event in self.events[self.current_event]:
            self.events[self.current_event][next_event] += 1 + random.random()/100
        else:
            if next_event in self.events:
                self.events[self.current_event][next_event] = 1 + random.random()/100
            else:   
                self.events[self.current_event][next_event] = 1 + random.random()/100
                self.events[next_event] = {next_event:0}
        self.current_event = next_event
    

thought = Dynamic()


def communication():
    global end
    global sock
    global thought
    
    while end == 0:
        
        c, addr = sock.accept() 
        #print 'connection from', addr
        
        response = 'ok'

        request = c.recv(1024)
        if request == 'close the server':
            end = 1
        else:
            if request == 'show dynamic':
                response = str(thought.events)
            else:
                thought.update(request)
            
        print thought.current_event
        
        c.send(response)
        c.close()
 
    sock.close()  

def counts():
    global thought
    
    while end == 0:
        
        time.sleep(4)
        next_event = max(thought.events[thought.current_event],key = thought.events[thought.current_event].get)
        thought.events[thought.current_event][next_event] += random.random()/100
        thought.current_event = next_event
        print thought.current_event
        

class thought_start():
    threading.Thread(target = counts).start()
    threading.Thread(target = communication).start()

class thought_stop():
    global end
    end = 1


