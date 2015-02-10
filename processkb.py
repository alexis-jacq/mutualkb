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

DEFAULT_MODEL = 'K_myself'
THRESHOLD = 0.2

class processKB:

    def __init__(self, kb):

        self.kb = kb

        #self.conflicts = conflictFinder.conflicts() 

        self.models = {DEFAULT_MODEL}

        #self.start_services()



    # ADD methods :
    #-------------------------------------------------
    def add(self, stmts, trust=None):

        if trust or trust==0:
            for model in list(self.models):
                self.kb.add(stmts, model, trust)
            else:
                for model in list(self.models):
                    self.kb.add(stmts, model)

        self.kb.save()

    def add_shared(self, stmts, trust=None):

        if trust or trust==0:
            for model in list(self.models):
                self.kb.add(stmts, model, trust)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                    self.kb.add([['%s'%(node_id), 'is', 'shared']], model, trust)
        else:
            for model in list(self.models):
                self.kb.add(stmts, model)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                    self.kb.add([['%s'%(node_id), 'is', 'shared']],model)

        self.kb.save()

    def add_common(self, stmts, trust=None):

        if trust or trust==0:
            for model in list(self.models):
                self.kb.add(stmts, model, trust)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                    self.kb.add([['%s'%(node_id), 'is', 'common']], model, trust)
        else:
            for model in list(self.models):
                self.kb.add(stmts, model)
                ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
                for node_id in ids:
                     self.kb.add([['%s'%(node_id), 'is', 'common']],model)

        self.kb.save()


    # SUB methods :
    #--------------
    def sub(self, stmts, untrust=None):

        if untrust or untrust==0:
            for model in list(self.models):
                self.kb.sub(stmts, model, untrust)
        else:
            for model in list(self.models):
                self.kb.sub(stmts, model)

        self.kb.save()


    # TEST methods :
    #---------------
    def __contains__(self, stmts):

        test = True
        for model in list(self.models):
            if self.kb.contains(stmts,model):
                pass
            else:
                test = False
                break
        return test


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

            self.start_services()

            time.sleep(3)
            print('first adds')

            story = False

            if story:

                ''' Gruffalo background '''
                self.add_common([[ 'mouse', 'rdf:type', 'Agent'],['fox','rdf:type','Agent']],[DEFAULT_MODEL],1)
                self.add_common([[ 'owl', 'rdf:type', 'Agent'],['snake','rdf:type','Agent']],[DEFAULT_MODEL],1)

                ''' Gruffalo story '''
                ''' ch.1 '''

                # narator speaks :
                model = [DEFAULT_MODEL]

                self.add([[ 'mouse', 'sees', 'fox']],model,1)
                self.add([[ 'fox', 'sees', 'mouse']],model,1)

                # fox speaks alone :
                model = ['M_myself:K_fox']

                self.add([[ 'self', 'wants_to_eat', 'mouse']],model,1)
                self.add([[ 'fox', 'wants_to_eat', 'mouse']],[DEFAULT_MODEL],1)

                # mouse speaks to the fox :
                idiot_model = ['M_myself:K_fox', 'M_myself:M_mouse:K_fox','M_myself:M_fox:K_mouse']
                smart_model = ['M_myself:K_mouse']

                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],idiot_model,0.8)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],smart_model,0)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],[DEFAULT_MODEL],0.5)

                # narator and mouse see that fox is scared:
                self.add([[ 'fox', 'fears', 'mouse'], ['fox', 'fears', 'gruffalo']],smart_model,0.8)
                self.add([[ 'fox', 'fears', 'mouse'], ['fox', 'fears', 'gruffalo']],[DEFAULT_MODEL],0.8)

                time.sleep(10)

                ''' end of ch.1'''

                print('##############')
                print('chapter 1 ok !')
                print('##############')

                ''' ch.2 '''

                # narator :
                model = [DEFAULT_MODEL]

                self.add([[ 'mouse', 'sees', 'owl']],model,1)
                self.add([[ 'owl', 'sees', 'mouse']],model,1)

                # owl speaks alone :
                model = ['M_myself:K_owl']

                self.add([[ 'owl', 'wants_to_eat', 'mouse']],model,1)
                self.add([[ 'owl', 'wants_to_eat', 'mouse']],[DEFAULT_MODEL],1)

                # mouse speaks to the owl :
                idiot_model = ['M_myself:K_owl', 'M_myself:M_mouse:K_owl','M_myself:M_owl:K_mouse']
                smart_model = ['M_myself:K_mouse']

                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'owl']],idiot_model,0.8)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'owl']],smart_model,0)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],[DEFAULT_MODEL],0.5)

                # narator and mouse see that owl is scared:
                self.add([[ 'owl', 'fears', 'mouse'], ['owl', 'fears', 'gruffalo']],smart_model,0.8)
                self.add([[ 'owl', 'fears', 'mouse'], ['owl', 'fears', 'gruffalo']],[DEFAULT_MODEL],0.8)

                time.sleep(10)

                ''' end of ch.2'''

                print('##############')
                print('chapter 2 ok !')
                print('##############')

                ''' ch.3 '''

                # narator :
                model = [DEFAULT_MODEL]

                self.add([[ 'mouse', 'sees', 'snake']],model,1)
                self.add([[ 'snake', 'sees', 'mouse']],model,1)

                # snake speaks alone :
                model = ['M_myself:K_snake']

                self.add([[ 'snake', 'wants_to_eat', 'mouse']],model,1)
                self.add([[ 'snake', 'wants_to_eat', 'mouse']],[DEFAULT_MODEL],1)

                # mouse speaks to the snake :
                idiot_model = ['M_myself:K_snake', 'M_myself:M_mouse:K_snake','M_myself:M_snake:K_mouse']
                smart_model = ['M_myself:K_mouse']

                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'snake']],idiot_model,0.9)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'snake']],smart_model,0)
                self.add([[ 'gruffalo', 'rdf:type', 'Agent'], ['gruffalo', 'wants_to_eat', 'fox']],[DEFAULT_MODEL],0.5)

                # narator and mouse see that snake is scared:
                self.add([[ 'snake', 'fears', 'mouse'], ['snake', 'fears', 'gruffalo']],smart_model,0.9)
                self.add([[ 'snake', 'fears', 'mouse'], ['snake', 'fears', 'gruffalo']],[DEFAULT_MODEL],0.9)

                time.sleep(10)

                ''' end of ch.3'''

                print('##############')
                print('chapter 3 ok !')
                print('##############')

                ''' ch.4 '''

                # narator :
                model = [DEFAULT_MODEL]

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
                model = [DEFAULT_MODEL]

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

                self.add([[ 'sally', 'rdf:type', 'Agent'],['anne','rdf:type','Agent']],[DEFAULT_MODEL],1)
                self.add([[ 'Agent', 'is', 'happy']],[DEFAULT_MODEL],1)

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

    kb = kb.KB()
    process = processKB(kb)

    process()
