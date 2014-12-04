from multiprocessing import Process

#from services.reasoner import start_reasoner, stop_reasoner
#from services.thought import start_thought, stop_thought

import kb
#import conflictFinder

DEFAULT_MODEL = 'K_Self'

class processKB:
    
    def __init__(self):

        self.kb = kb.KB()

        #self.conflicts = conflictFinder.conflicts() 
        
        self.models = {DEFAULT_MODEL}
        
        #self.start_services()



    # ADD methods :
    #-------------------------------------------------
    def add(self, stmts, models=None, likelihood=None):
                                                                
        if likelihood:
            if models:
                for model in models:
                    matters = self.kb.add(stmts, model, likelihood)
            else:
                matters = self.kb.add(stmts, DEFAULT_MODEL)
        else:
            if models:  
                for model in models:
                    matters = self.kb.add(stmts, model)
            else:       
                matters = self.kb.add(stmts, DEFAULT_MODEL)

        for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)

    def add_physic(self, stmts, models=None, likelihood=None):
                                                        
        if likelihood:
            if models:
                for model in models:
                    matters = self.kb.add(stmts, model, likelihood, "physic")
            else:
                matters = self.kb.add(stmts, DEFAULT_MODEL, "physic")
        else:
            if models:  
                for model in models:
                    matters = self.kb.add(stmts, model, "physic")
            else:       
                matters = self.kb.add(stmts, DEFAULT_MODEL, "physic")

        for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)
    
    def add_general(self, stmts, models=None, likelihood=None):

        if likelihood:
            if models:
                for model in models:
                    matters = self.kb.add(stmts, model, likelihood, "general")
            else:
                matters = self.kb.add(stmts, DEFAULT_MODEL, "general")
        else:
            if models:  
                for model in models:
                    matters = self.kb.add(stmts, model, "general")
            else:           
                matters = self.kb.add(stmts, DEFAULT_MODEL, "general")
    
        for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)

    def add_conceptual(self, stmts, models=None, likelihood=None):
            
        if likelihood:
            if models:
                for model in models:
                    matters = self.kb.add(stmts, model, likelihood, "conceptual")
            else:
                matters = self.kb.add(stmts, DEFAULT_MODEL, "conceptual")
        else:
            if models:  
                for model in models:
                    matters = self.kb.add(stmts, model, "conceptual")
            else:           
                matters = self.kb.add(stmts, DEFAULT_MODEL, "conceptual")

        for model in models:
            self.conflicts.updtate(stmts, model)
            self.conflicts.solve(stmts, model)



    # SUB methods :
    #--------------------------------------------------
    def sub(self, stmts, models=None, likelihood=None):

        if likelihood:
            if models:
                for model in models:
                    self.kb.sub(stmts, model, likelihood)
            else:
                self.kb.sub(stmts, DEFAULT_MODEL)
        else:
            if models:  
                for model in models:
                    self.kb.sub(stmts, model)
            else:    
                self.kb.sub(stmts, DEFAULT_MODEL)



    # SERVICES methods
    #-----------------------------------------
    '''
    def start_services(self, *args):

        self._reasoner = Process(target = start_reasoner, args = ('kb.db',))
        self._reasoner.start()

        #self._thought = Process(target = start_thought, args = ('kb.db',))
        #self._thought.start()

    def stop_services(self):
        self._reasoner.terminate()
        #self._thought.terminate()

        self._reasoner.join()
        #self._thought.join()



# TESTING
#------------------------------
if __name__=='__main__':

    processkb = processKB()

    # processkb.add...

    # wait 1 min 

    processkb.stop_services()
'''




















