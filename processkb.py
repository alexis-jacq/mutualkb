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
                                                                
        if likelihood or likelihood==0:
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
                                                        
        if likelihood or likelihood==0:
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

        if likelihood or likelihood==0:
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

    def add_specific(self, stmts, models=None, likelihood=None):
            
        if likelihood or likelihood==0:
            if models:
                for model in models:
                    self.kb.add(stmts, model, likelihood, "specific")
            else:
                self.kb.add(stmts, DEFAULT_MODEL, likelihood, "specific")
        else:
            if models:  
                for model in models:
                    self.kb.add(stmts, model, 0.5, "specific")
            else:           
                self.kb.add(stmts, DEFAULT_MODEL, 0.5, "specific")

        '''for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)'''
        self.kb.save()



    # SUB methods :
    #--------------------------------------------------
    def sub(self, stmts, models=None, unlikelihood=None):

        if unlikelihood or unlikelihood==0:
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
            
            ''' basic tests ( classes )
            self.add_general([[ 'self', 'rdf:type', 'robot'],['robot','rdfs:subClassOf','agent']],DEFAULT_MODEL,0.7)
            self.add_general([['agent','rdfs:subClassOf','humanoide'],['human','rdfs:subClassOf','animals']],DEFAULT_MODEL,0.5)
            self.add_general([['robot','owl:equivalentClass','machine'],['machine','owl:equivalentClass','automate']],DEFAULT_MODEL,0.2)
            '''
            '''
            basic tests ( mutual knowledge )
            self.add_general([['zoro', 'rdf:type', 'agent'], ['vincent', 'rdf:type', 'agent'], ['pierre', 'rdf:type', 'agent'], ['marc', 'rdf:type', 'agent']],DEFAULT_MODEL,0.5)
            self.add_specific([['zoro', 'knows', 'vincent'],['marc', 'knows', 'pierre']],DEFAULT_MODEL,0.5)
            self.add_general([['superman', 'rdf:type', 'agent']],DEFAULT_MODEL,0.5)
            '''
            
            story = True
            
            if story:
            
                ''' Gruffalo background '''
                self.add_general([[ 'mouse', 'rdf:type', 'agent'],['fox','rdf:type','agent']],DEFAULT_MODEL,1)
                self.add_general([[ 'owl', 'rdf:type', 'agent'],['snake','rdf:type','agent']],DEFAULT_MODEL,1)
                
                ''' Gruffalo story '''
                ''' ch.1 '''
                
                # narator speaks :
                model = DEFAULT_MODEL
                
                self.add_general([[ 'mouse', 'sees', 'fox']],model,1)
                self.add_general([[ 'fox', 'sees', 'mouse']],model,1)
                
                # fox speaks alone :
                model = ['M_myself:K_fox']
                
                self.add_general([[ 'self', 'wants_to_eat', 'mouse']],model,1)
                self.add_general([[ 'fox', 'wants_to_eat', 'mouse']],DEFAULT_MODEL,1)
                
                # mouse speaks to the fox :
                idiot_model = ['M_myself:K_fox', 'M_myself:M_mouse:K_fox','M_myself:M_fox:K_mouse']
                smart_model = ['M_myself:K_mouse']
                
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'fox']],idiot_model,0.8)
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'fox']],smart_model,0)
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'fox']],DEFAULT_MODEL,0.5)
                
                # narator and mouse see that fox is scared:
                self.add_general([[ 'fox', 'fears', 'mouse'], ['fox', 'fears', 'gruffalo']],smart_model,0.8)
                self.add_general([[ 'fox', 'fears', 'mouse'], ['fox', 'fears', 'gruffalo']],DEFAULT_MODEL,0.8)
                
                time.sleep(10)
                
                ''' end of ch.1'''
                
                print('##############')
                print('chapter 1 ok !')
                print('##############')
            
                ''' ch.2 '''
                
                # narator :
                model = DEFAULT_MODEL
                
                self.add_general([[ 'mouse', 'sees', 'owl']],model,1)
                self.add_general([[ 'owl', 'sees', 'mouse']],model,1)
                
                # owl speaks alone :
                model = ['M_myself:K_owl']
                
                self.add_general([[ 'owl', 'wants_to_eat', 'mouse']],model,1)
                self.add_general([[ 'owl', 'wants_to_eat', 'mouse']],DEFAULT_MODEL,1)
                
                # mouse speaks to the owl :
                idiot_model = ['M_myself:K_owl', 'M_myself:M_mouse:K_owl','M_myself:M_owl:K_mouse']
                smart_model = ['M_myself:K_mouse']
                
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'owl']],idiot_model,0.8)
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'owl']],smart_model,0)
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'fox']],DEFAULT_MODEL,0.5)
                
                # narator and mouse see that owl is scared:
                self.add_general([[ 'owl', 'fears', 'mouse'], ['owl', 'fears', 'gruffalo']],smart_model,0.8)
                self.add_general([[ 'owl', 'fears', 'mouse'], ['owl', 'fears', 'gruffalo']],DEFAULT_MODEL,0.8)
                
                time.sleep(10)
                
                ''' end of ch.2'''
                
                print('##############')
                print('chapter 2 ok !')
                print('##############')
                
                ''' ch.3 '''
                
                # narator :
                model = DEFAULT_MODEL
                
                self.add_general([[ 'mouse', 'sees', 'snake']],model,1)
                self.add_general([[ 'snake', 'sees', 'mouse']],model,1)
                
                # snake speaks alone :
                model = ['M_myself:K_snake']
                
                self.add_general([[ 'snake', 'wants_to_eat', 'mouse']],model,1)
                self.add_general([[ 'snake', 'wants_to_eat', 'mouse']],DEFAULT_MODEL,1)
                
                # mouse speaks to the snake :
                idiot_model = ['M_myself:K_snake', 'M_myself:M_mouse:K_snake','M_myself:M_snake:K_mouse']
                smart_model = ['M_myself:K_mouse']
                
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'snake']],idiot_model,0.9)
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'snake']],smart_model,0)
                self.add_general([[ 'gruffalo', 'rdf:type', 'agent'], ['gruffalo', 'wants_to_eat', 'fox']],DEFAULT_MODEL,0.5)
                
                # narator and mouse see that snake is scared:
                self.add_general([[ 'snake', 'fears', 'mouse'], ['snake', 'fears', 'gruffalo']],smart_model,0.9)
                self.add_general([[ 'snake', 'fears', 'mouse'], ['snake', 'fears', 'gruffalo']],DEFAULT_MODEL,0.9)
                
                time.sleep(10)
                
                ''' end of ch.3'''
                
                print('##############')
                print('chapter 3 ok !')
                print('##############')
                
                ''' ch.4 '''
                
                # narator :
                model = DEFAULT_MODEL
                
                self.add_general([[ 'mouse', 'sees', 'gruffalo']],model,1)
                self.add_general([[ 'gruffalo', 'sees', 'mouse']],model,1)
                
                # gruffalo speaks alone :
                model = ['M_myself:K_gruffalo','K_myself']
                
                self.add_general([[ 'gruffalo', 'wants_to_eat', 'mouse']],model,1)
                
                # mouse speaks to the gruffalo :
                idiot_model = ['M_myself:K_gruffalo', 'M_myself:M_mouse:K_gruffalo','M_myself:M_gruffalo:K_mouse']
                smart_model = ['M_myself:K_mouse', 'K_myself']
                
                self.add_general([['snake', 'fears', 'mouse']],idiot_model,0.4)
                self.add_general([['owl', 'fears', 'mouse']],idiot_model,0.4)
                self.add_general([['fox', 'fears', 'mouse']],idiot_model,0.4)
                
                # everybody knows that gruffalo is not so idiot :
                self.add_general([[ 'gruffalo', 'fears', 'mouse']],smart_model,0.4)
                
                time.sleep(10)
                
                ''' end of ch.4'''
                
                print('##############')
                print('chapter 4 ok !')
                print('##############')
                
                ''' ch.5 '''
                
                # narator :
                model = DEFAULT_MODEL
                
                self.add_general([[ 'gruffalo', 'sees', 'snake']],model,1)
                self.add_general([[ 'gruffalo', 'sees', 'owl']],model,1)
                self.add_general([[ 'gruffalo', 'sees', 'fox']],model,1)
                
                # gruffalo and mouse see that other animals are scared :
                model = ['M_myself:K_mouse', 'K_myself', 'M_myself:K_gruffalo', 'M_myself:M_mouse:K_gruffalo','M_myself:M_gruffalo:K_mouse']
                
                self.add_general([['fox', 'fears', '?' ]],model,0.9)
                self.add_general([['owl', 'fears', '?' ]],model,0.9)
                self.add_general([['snake', 'fears', '?' ]],model,0.9) 
                
                self.add_general([[ 'gruffalo', 'fears', 'mouse']],model,0.9)
                
                time.sleep(15)
                
                print('##############')
                print('all history ok !')
                print('##############')
                
            
            
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




















