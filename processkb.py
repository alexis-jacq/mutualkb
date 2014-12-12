import logging; logger = logging.getLogger('mylog');

import time

from multiprocessing import Process
import socket

from reasoner import reasoner_start, reasoner_stop
from thought import thought_start, thought_stop, port

#import reasoner
#import thought

import kb
#import conflictFinder

DEFAULT_MODEL = ['K_myself']
THRESHOLD = 0.2

class processKB:
    
    def __init__(self):

        self.kb = kb.KB()

        #self.conflicts = conflictFinder.conflicts() 
        
        self.models = {DEFAULT_MODEL[0]}
        
        self.start_services()



    # ADD methods :
    #-------------------------------------------------
    def add(self, stmts, models=None, likelihood=None):
                                                                
        if likelihood:
            if models:
                for model in models:
                    self.kb.add(stmts, model, likelihood)
            else:
                self.kb.add(stmts, DEFAULT_MODEL, likelihood)
        else:
            if models:  
                for model in models:
                    self.kb.add(stmts, model)
            else:       
                self.kb.add(stmts, DEFAULT_MODEL)

        '''for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)'''
        self.kb.save()

    def add_physic(self, stmts, models=None, likelihood=None):
                                                        
        if likelihood:
            if models:
                for model in models:
                    self.kb.add(stmts, model, likelihood, "physical")
            else:
                self.kb.add(stmts, DEFAULT_MODEL, likelihood, "physical")
        else:
            if models:  
                for model in models:
                    self.kb.add(stmts, model, 0.5, "physical")
            else:       
                self.kb.add(stmts, DEFAULT_MODEL, 0.5,  "physical")

        '''for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)'''
        self.kb.save()
    
    def add_general(self, stmts, models=None, likelihood=None):

        if likelihood:
            if models:
                for model in models:
                    self.kb.add(stmts, model, likelihood, "general")
            else:
                self.kb.add(stmts, DEFAULT_MODEL, likelihood, "general")
        else:
            if models:  
                for model in models:
                    self.kb.add(stmts, model, 0.5, "general")
            else:           
                self.kb.add(stmts, DEFAULT_MODEL, 0.5, "general")
    
        ''''for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)'''
        self.kb.save()

    def add_conceptual(self, stmts, models=None, likelihood=None):
            
        if likelihood:
            if models:
                for model in models:
                    self.kb.add(stmts, model, likelihood, "conceptual")
            else:
                self.kb.add(stmts, DEFAULT_MODEL, likelihood, "conceptual")
        else:
            if models:  
                for model in models:
                    self.kb.add(stmts, model, 0.5, "conceptual")
            else:           
                self.kb.add(stmts, DEFAULT_MODEL, 0.5, "conceptual")

        '''for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)'''
        self.kb.save()



    # SUB methods :
    #--------------------------------------------------
    def sub(self, stmts, models=None, unlikelihood=None):

        if unlikelihood:
            if models:
                for model in models:
                    self.kb.sub(stmts, model, unlikelihood)
            else:
                self.kb.sub(stmts, DEFAULT_MODEL)
        else:
            if models:  
                for model in models:
                    self.kb.sub(stmts, model)
            else:    
                self.kb.sub(stmts, DEFAULT_MODEL)
                
        self.kb.save()



    # SERVICES methods
    #-----------------------------------------
    def start_services(self, *args):

        self._reasoner = Process(target = reasoner_start)
        self._reasoner.start()

        self._thought = Process(target = thought_start, args = (self.kb,))
        self._thought.start()
        logger.info('services started')

    def stop_services(self):
        self._reasoner.terminate()
        self._thought.terminate()

        self._reasoner.join()
        self._thought.join()
                
        
    def __call__(self, *args):
        try:
            # just for testing cascade of new nodes:
            
            time.sleep(3)
            print('first adds')
            
            self.add_general([[ 'self', 'rdf:type', 'robot'],['robot','rdfs:subClassOf','agent']],DEFAULT_MODEL,0.5)
            self.add_general([['agent','rdfs:subClassOf','humanoide'],['human','rdfs:subClassOf','animals']],DEFAULT_MODEL,0.5)
            self.add_general([['robot','owl:equivalentClass','machine'],['machine','owl:equivalentClass','automate']],DEFAULT_MODEL,0.5)
            self.add_general([['zoro', 'rdf:type', 'agent'], ['vincent', 'rdf:type', 'agent'], ['pierre', 'rdf:type', 'agent'], ['marc', 'rdf:type', 'agent']],DEFAULT_MODEL,0.5)
            self.add_conceptual([['zoro', 'knows', 'vincent'],['marc', 'knows', 'pierre']],DEFAULT_MODEL,0.5)
            self.add_general([['superman', 'rdf:type', 'agent']],DEFAULT_MODEL,0.5)
            
            time.sleep(5)
            
            print('second adds')
            self.add_physic([['table', 'in', 'world']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            self.add_physic([['nothing', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            self.add_physic([['superman', 'behind', 'table']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['nothing', 'on', 'table']],DEFAULT_MODEL,0.1)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            self.add_conceptual([['superman', 'looks', 'ball']],DEFAULT_MODEL,0.6)
            time.sleep(1)
            self.add_conceptual([['ball', 'exploses', 'true']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            
            self.add_conceptual([['ball', 'exploses', 'true']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.1)
            time.sleep(1)
            self.add_physic([['nothing', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            
            self.add_physic([['superman', 'behind', 'table']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['nothing', 'on', 'table']],DEFAULT_MODEL,0.1)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            self.add_conceptual([['superman', 'looks', 'ball']],DEFAULT_MODEL,0.6)
            time.sleep(1)
            self.add_conceptual([['ball', 'exploses', 'true']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_conceptual([['ball', 'exploses', 'true']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.1)
            time.sleep(1)
            self.add_physic([['nothing', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            
            self.add_physic([['superman', 'behind', 'table']],DEFAULT_MODEL,0.1)
            time.sleep(1)
            
            self.add_physic([['zoro', 'behind', 'table']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['nothing', 'on', 'table']],DEFAULT_MODEL,0.1)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            self.add_conceptual([['zoro', 'looks', 'ball']],DEFAULT_MODEL,0.6)
            time.sleep(1)
            self.add_conceptual([['ball', 'exploses', 'false']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_conceptual([['ball', 'exploses', 'false']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            
            self.add_physic([['zoro', 'behind', 'table']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['nothing', 'on', 'table']],DEFAULT_MODEL,0.1)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.9)
            time.sleep(1)
            self.add_conceptual([['zoro', 'looks', 'ball']],DEFAULT_MODEL,0.6)
            time.sleep(1)
            self.add_conceptual([['ball', 'exploses', 'false']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_conceptual([['ball', 'exploses', 'false']],DEFAULT_MODEL,0.8)
            time.sleep(1)
            self.add_physic([['ball', 'on', 'table']],DEFAULT_MODEL,0.9)
            
            
            while True:
                '''listend world or dialogues'''
                pass
                
        except KeyboardInterrupt:
            self.stop_services()
            logger.info("Bye bye")


# TESTING
#------------------------------
if __name__=='__main__':
    
    from ansistrm import ColorizingStreamHandler
    
    console = ColorizingStreamHandler()
    
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)-15s: %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    process = processKB()

    process()




















