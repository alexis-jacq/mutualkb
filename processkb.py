import logging; logger = logging.getLogger('mylog');

import time

from multiprocessing import Process
import socket

from reasoner import reasoner_start, reasoner_stop
from thought import thought_start, thought_stop

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

        self.kb.save()

    def add_shared(self, stmts, models=None, likelihood=None):

        if likelihood or likelihood==0:
            if models:
                for model in models:
                    self.kb.add(stmts, model, likelihood)
                    ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                    for node_id in ids:
                        self.kb.add([['%s'%(node_id), 'is', 'shared']], model, likelihood)
            else:
                self.kb.add(stmts, DEFAULT_MODEL, likelihood)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                    self.kb.add([['%s'%(node_id), 'is', 'shared']], DEFAULT_MODEL, likelihood)
        else:
            if models:
                for model in models:
                    self.kb.add(stmts, model)
                    ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                    for node_id in ids:
                        self.kb.add([['%s'%(node_id), 'is', 'shared']],model)
            else:
                self.kb.add(stmts, DEFAULT_MODEL)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                    self.kb.add([['%s'%(node_id), 'is', 'shared']],DEFAULT_MODEL)

        self.kb.save()

    def add_common(self, stmts, models=None, likelihood=None):

        if likelihood or likelihood==0:
            if models:
                for model in models:
                    self.kb.add(stmts, model, likelihood)
                    ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                    for node_id in ids:
                        self.kb.add([['%s'%(node_id), 'is', 'common']], model, likelihood)
            else:
                self.kb.add(stmts, DEFAULT_MODEL, likelihood)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                    self.kb.add([['%s'%(node_id), 'is', 'common']], DEFAULT_MODEL, likelihood)
        else:
            if models:
                for model in models:
                    self.kb.add(stmts, model)
                    ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                    for node_id in ids:
                        self.kb.add([['%s'%(node_id), 'is', 'common']],model)
            else:
                self.kb.add(stmts, DEFAULT_MODEL)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                    self.kb.add([['%s'%(node_id), 'is', 'common']],DEFAULT_MODEL)

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
            self.add([[ 'self', 'rdf:type', 'robot'],['robot','rdfs:subClassOf','Agent']],DEFAULT_MODEL,0.7)
            self.add([['Agent','rdfs:subClassOf','humanoide'],['human','rdfs:subClassOf','animals']],DEFAULT_MODEL,0.5)
            self.add([['robot','owl:equivalentClass','machine'],['machine','owl:equivalentClass','automate']],DEFAULT_MODEL,0.2)
            '''
            '''
            basic tests ( mutual knowledge )
            self.add([['zoro', 'rdf:type', 'Agent'], ['vincent', 'rdf:type', 'Agent'], ['pierre', 'rdf:type', 'Agent'], ['marc', 'rdf:type', 'Agent']],DEFAULT_MODEL,0.5)
            self.add_specific([['zoro', 'knows', 'vincent'],['marc', 'knows', 'pierre']],DEFAULT_MODEL,0.5)
            self.add([['superman', 'rdf:type', 'Agent']],DEFAULT_MODEL,0.5)
            '''

            story = False

            if story:

                ''' Gruffalo background '''
                self.add_common([[ 'mouse', 'rdf:type', 'Agent'],['fox','rdf:type','Agent']],DEFAULT_MODEL,1)
                self.add_common([[ 'owl', 'rdf:type', 'Agent'],['snake','rdf:type','Agent']],DEFAULT_MODEL,1)

                ''' Gruffalo story '''
                ''' ch.1 '''

                # narator speaks :
                model = DEFAULT_MODEL

                self.add([[ 'mouse', 'sees', 'fox']],model,1)
                self.add([[ 'fox', 'sees', 'mouse']],model,1)

                # fox speaks alone :
                model = ['M_myself:K_fox']

                self.add([[ 'self', 'wants_to_eat', 'mouse']],model,1)
                self.add([[ 'fox', 'wants_to_eat', 'mouse']],DEFAULT_MODEL,1)

                # mouse speaks to the fox :
                idiot_model = ['M_myself:K_fox', 'M_myself:M_mouse:K_fox','M_myself:M_fox:K_mouse']
                smart_model = ['M_myself:K_mouse']

                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],idiot_model,0.8)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],smart_model,0)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],DEFAULT_MODEL,0.5)

                # narator and mouse see that fox is scared:
                self.add([[ 'fox', 'fears', 'mouse'], ['fox', 'fears', 'gruffalo']],smart_model,0.8)
                self.add([[ 'fox', 'fears', 'mouse'], ['fox', 'fears', 'gruffalo']],DEFAULT_MODEL,0.8)

                time.sleep(10)

                ''' end of ch.1'''

                print('##############')
                print('chapter 1 ok !')
                print('##############')

                ''' ch.2 '''

                # narator :
                model = DEFAULT_MODEL

                self.add([[ 'mouse', 'sees', 'owl']],model,1)
                self.add([[ 'owl', 'sees', 'mouse']],model,1)

                # owl speaks alone :
                model = ['M_myself:K_owl']

                self.add([[ 'owl', 'wants_to_eat', 'mouse']],model,1)
                self.add([[ 'owl', 'wants_to_eat', 'mouse']],DEFAULT_MODEL,1)

                # mouse speaks to the owl :
                idiot_model = ['M_myself:K_owl', 'M_myself:M_mouse:K_owl','M_myself:M_owl:K_mouse']
                smart_model = ['M_myself:K_mouse']

                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'owl']],idiot_model,0.8)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'owl']],smart_model,0)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],DEFAULT_MODEL,0.5)

                # narator and mouse see that owl is scared:
                self.add([[ 'owl', 'fears', 'mouse'], ['owl', 'fears', 'gruffalo']],smart_model,0.8)
                self.add([[ 'owl', 'fears', 'mouse'], ['owl', 'fears', 'gruffalo']],DEFAULT_MODEL,0.8)

                time.sleep(10)

                ''' end of ch.2'''

                print('##############')
                print('chapter 2 ok !')
                print('##############')

                ''' ch.3 '''

                # narator :
                model = DEFAULT_MODEL

                self.add([[ 'mouse', 'sees', 'snake']],model,1)
                self.add([[ 'snake', 'sees', 'mouse']],model,1)

                # snake speaks alone :
                model = ['M_myself:K_snake']

                self.add([[ 'snake', 'wants_to_eat', 'mouse']],model,1)
                self.add([[ 'snake', 'wants_to_eat', 'mouse']],DEFAULT_MODEL,1)

                # mouse speaks to the snake :
                idiot_model = ['M_myself:K_snake', 'M_myself:M_mouse:K_snake','M_myself:M_snake:K_mouse']
                smart_model = ['M_myself:K_mouse']

                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'snake']],idiot_model,0.9)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'snake']],smart_model,0)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],DEFAULT_MODEL,0.5)

                # narator and mouse see that snake is scared:
                self.add([[ 'snake', 'fears', 'mouse'], ['snake', 'fears', 'gruffalo']],smart_model,0.9)
                self.add([[ 'snake', 'fears', 'mouse'], ['snake', 'fears', 'gruffalo']],DEFAULT_MODEL,0.9)

                time.sleep(10)

                ''' end of ch.3'''

                print('##############')
                print('chapter 3 ok !')
                print('##############')

                ''' ch.4 '''

                # narator :
                model = DEFAULT_MODEL

                self.add([[ 'mouse', 'sees', 'gruffalo']],model,1)
                self.add([[ 'gruffalo', 'sees', 'mouse']],model,1)

                # gruffalo speaks alone :
                model = ['M_myself:K_gruffalo','K_myself']

                self.add([[ 'gruffalo', 'wants_to_eat', 'mouse']],model,1)

                # mouse speaks to the gruffalo :
                idiot_model = ['M_myself:K_gruffalo', 'M_myself:M_mouse:K_gruffalo','M_myself:M_gruffalo:K_mouse']
                smart_model = ['M_myself:K_mouse', 'K_myself']

                self.add([['snake', 'fears', 'mouse']],idiot_model,0.4)
                self.add([['owl', 'fears', 'mouse']],idiot_model,0.4)
                self.add([['fox', 'fears', 'mouse']],idiot_model,0.4)

                # everybody knows that gruffalo is not so idiot :
                self.add([[ 'gruffalo', 'fears', 'mouse']],smart_model,0.4)

                time.sleep(10)

                ''' end of ch.4'''

                print('##############')
                print('chapter 4 ok !')
                print('##############')

                ''' ch.5 '''

                # narator :
                model = DEFAULT_MODEL

                self.add([[ 'gruffalo', 'sees', 'snake']],model,1)
                self.add([[ 'gruffalo', 'sees', 'owl']],model,1)
                self.add([[ 'gruffalo', 'sees', 'fox']],model,1)

                # gruffalo and mouse see that other animals are scared :
                model = ['M_myself:K_mouse', 'K_myself', 'M_myself:K_gruffalo', 'M_myself:M_mouse:K_gruffalo','M_myself:M_gruffalo:K_mouse']

                self.add([['fox', 'fears', '?' ]],model,0.9)
                self.add([['owl', 'fears', '?' ]],model,0.9)
                self.add([['snake', 'fears', '?' ]],model,0.9) 

                self.add([[ 'gruffalo', 'fears', 'mouse']],model,0.9)

                time.sleep(15)

                print('##############')
                print('all history ok !')
                print('##############')

            else:

                self.add([[ 'sally', 'rdf:type', 'Agent'],['anne','rdf:type','Agent']],DEFAULT_MODEL,1)
                self.add([[ 'Agent', 'is', 'happy']],DEFAULT_MODEL,1)

                model = ['M_myself:K_sally','M_myself:K_anne','K_myself']

                self.add([['ball','inside','box1']],model,1)

                model = ['M_myself:K_anne','K_myself']

                self.add([['ball','inside','box1']],model,0)
                self.add([['ball','inside','box2']],model,1)



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
