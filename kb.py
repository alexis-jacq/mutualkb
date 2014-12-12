import logging; logger = logging.getLogger('mylog');
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import numpy
import socket
import random     
import threading
import time  
import Queue

KBNAME = 'kb.db'
TABLENAME = 'nodes'
TABLE = ''' CREATE TABLE IF NOT EXISTS %s
            ("subject" TEXT NOT NULL , 
            "predicate" TEXT NOT NULL , 
            "object" TEXT NOT NULL , 
            "model" TEXT NOT NULL ,
            "agent" TEXT NOT NULL DEFAULT "myself",
            "likelihood" FLOAT DEFAULT 0.5 NOT NULL,
            "topic" TEXT DEFAULT "conceptual" NOT NULL,
            "assumed" BOOLEAN DEFAULT 0 NOT NULL,
            "active" INT DEFAULT 0 NOT NULL,
            "matter" FLOAT DEFAULT 0.5 NOT NULL,
            "id" TEXT PRIMARY KEY NOT NULL UNIQUE)'''

DEFAULT_MODEL = 'K_myself'


class KB:

    def __init__(self):
        self.conn = sqlite3.connect(KBNAME)
        self.create_kb()
        logger.info('new knowledge base created')

    def create_kb(self):
        with self.conn:
            self.conn.execute(TABLE % TABLENAME)
            self.conn.execute('''DELETE FROM %s''' % TABLENAME)

    def save(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
        
    def wait_turn(self):
        while True:
            try:
                self.conn.execute('''SELECT * FROM %s''' % TABLENAME)
                break
            except sqlite3.OperationalError:
                pass



    # REASON/WORLD/DIALOG methods
    #-------------------------

    def add(self, stmts, model, likelihood=None, topic=None):
        ''' stmts = statements = list of triplet 'subject, predicate, object'. ex: [[ s1, p1, o1], [s2, p2, o2], ...]
        this methode adds nodes to the table with statments attached to the selected model and increases likelihoods
        it returns a list of value that measur the importance of the added nodes to capt attention'''
        
        if isinstance(likelihood,str):
            logger.warning('maybe you want to enter topic without likelihood')
            topic = likelihood
            likelihood = None

        if likelihood:
            llh = likelihood
        else:
            llh = 0.5
        
        self.wait_turn()

        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
        

        for node_id in ids:
            cursor=self.conn.cursor()
            try:
                cursor.execute('''SELECT likelihood FROM %s WHERE (id = ?)''' % TABLENAME, node_id)
                hold_llh = cursor.fetchone()[0]
            except TypeError:
                hold_llh = 0
            matter = numpy.absolute(llh-hold_llh)
            self.conn.executemany('''UPDATE %s SET matter='%f' WHERE id=?''' % (TABLENAME, matter), ids)
            
        nodes = [[ s, p, o, model, "%s%s%s%s"%(s,p,o, model) ] for s,p,o in stmts]
        self.conn.executemany('''INSERT OR IGNORE INTO %s
                       (subject, predicate, object, model, id )
                       VALUES (?, ?, ?, ?, ?)''' % TABLENAME, nodes)
            
        if likelihood:
            self.conn.executemany('''UPDATE %s SET likelihood=((SELECT likelihood)*%f
                          /((SELECT likelihood)*%f + (1-(SELECT likelihood))*(1-%f))) 
                          WHERE id=?''' % (TABLENAME, likelihood, likelihood, likelihood), ids)

        if topic:
            if topic not in ['general', 'physical', 'conceptual']:
                logger.warning('not handled topic : <<%s>>, replacing by default topic (conceptual)' % topic) 
                topic='conceptual'
            self.conn.executemany('''UPDATE %s SET topic='%s' WHERE id=?''' % (TABLENAME, topic), ids)

        agent = model.replace('_',' ').split()[-1]
        self.conn.executemany('''UPDATE %s SET agent="%s" WHERE id=?''' % (TABLENAME, agent), ids)
        
        self.save()

        
    def sub(self, stmts, model, unlikelihood=None):
        ''' the unlikeliihood is the likelihood for the statement to be false, for ex, the likelihood of a contrary statement '''
        '''stmts = this methode decreases likelihoods of nodes with statments attached to the selected model '''

        self.wait_turn

        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]

        if likelihood:
            self.conn.executemany('''UPDATE %s SET likelihood=((SELECT likelihood)*(1-%f)
                          /((SELECT likelihood)*(1-%f) + (1-(SELECT likelihood))*(%f))) 
                          WHERE id=?''' % (TABLENAME, unlikelihood, unlikelihood, unlikelihood) , ids)
        self.save()
    

    def assum(self, stmts, model):

        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
        
        self.conn.executemany('''UPDATE %s SET assumed=1 WHERE id=?''' % TABLENAME, ids)
        
        self.save()
        
    def refute(self, stmts, model):

        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]

        self.conn.executemany('''UPDATE %s SET assumed=0 WHERE id=?''' % TABLENAME, ids)
        
        self.save()

    
    # THOUGHT methods
    #----------------------------
    
    def fire(self, ids):
        '''stmts = this methode actives the selected nodes'''
    
        self.conn.executemany('''UPDATE %s SET active=5 WHERE id=?''' % TABLENAME, ids)
        self.save()


    def douse(self, ids):
        '''stmts = this methode disactives the selected nodes '''

        self.conn.executemany('''UPDATE %s SET active=0 WHERE id=?''' % TABLENAME, ids)
        self.save()


    def kill(self, ids):
        '''this methode removes the selected nodes '''

        self.conn.executemany('''DELETE FROM %s WHERE id=?''' % TABLENAME, ids)
        self.save()


    # TEST methods
    #---------------------------------
    
    def testumpty(self):
    
        
        try :
            test = {row[0] for row in self.conn.execute('''SELECT subject FROM %s 
                WHERE (predicate='ise')
                ''' % TABLENAME )}              
        except sqlite3.OperationalError:
            test = {}
        return test


# TESTING
#-----------------------
if __name__== '__main__':
    
    kb =  KB()

    #kb.conn.execute('''UPDATE nodes SET active=0''')

    matters = kb.add([[ 'self', 'rdf:type', 'robot'],['clouds','hide','mountains']],DEFAULT_MODEL,0.5,'general')
    #print(matters)
    #kb.sub([['clouds','hide','mountains']],DEFAULT_MODEL,0.3)
    matter = kb.add([['clouds','hide','mountains']],DEFAULT_MODEL, 0.6)
    #print(matter)
    kb.add([['robot','rdfs:subClassOf','agent'],['agent','rdfs:subClassOf','humanoide'],['clouds','rdfs:subClassOf','landscape'],['human','rdfs:subClassOf','animals']],DEFAULT_MODEL,0.5,'general')

    kb.add([['robot','owl:equivalentClass','machine'],['machine','owl:equivalentClass','automate']],DEFAULT_MODEL,0.5,'general')

    kb.add([['animals','rdfs:subClassOf','alive'], ['human','rdfs:subClassOf','agent']],DEFAULT_MODEL,0.5,'general')

    kb.fire([('selfrdf:typerobotK_self',),('animalsrdfs:subClassOfaliveK_self',),('humanrdfs:subClassOfagentK_self',)])

    kb.add([['alexis', 'rdf:type', 'agent'], ['vincent', 'rdf:type', 'agent'], ['pierre', 'rdf:type', 'agent'], ['marc', 'rdf:type', 'agent']],DEFAULT_MODEL,0.5,'general')

    kb.add([['alexis', 'knows', 'vincent'],['marc', 'knows', 'pierre']],DEFAULT_MODEL)
    
    #test = kb.testumpty()
    #if test:
    #       print('ok')
    #else:
    #       print('ko')
    
    #kb.kill([("%s%s%s%s"%('self','is','robot',DEFAULT_MODEL),)])

    #kb.add([[ 'self', 'is', 'robot'],['clouds','hide','mountains']],DEFAULT_MODEL,0.6)

    kb.save()
    kb.close()

