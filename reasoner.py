import logging; logger = logging.getLogger("minimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import Queue

from processkb import DEFAULT_MODEL
from kb import TABLENAME, KBNAME

REASONER_RATE = 5 #Hz
END = False

# add M operator et K operator

class OntoClass():

    def __init__(self, name):
        self.name = name
        self.parents = set()
        self.children = set()
        self.instances = set()
        self.equivalents = set()

class reasoner():

    SYMMETRIC_PREDICATES = {"owl:differentFrom", "owl:sameAs", "owl:disjointWith"}

    def __init__(self, database = KBNAME):
        self.db = sqlite3.connect(':memory:')
        self.shareddb = sqlite3.connect(database)

        query = None
        for line in self.shareddb.iterdump():
            if TABLENAME in line:
                query = line
                break
        self.db.executescript(query)

        self.running = True

    def get_models(self):
        with self.db:
            return [row[0] for row in self.db.execute("SELECT DISTINCT model FROM %s" % TABLENAME)]


    # ONTOLOGY methods ==> general knowledge
    #---------------------------------------------

    def get_onto(self, db, model = DEFAULT_MODEL):

        onto = {}

        rdftype = None
        subclassof = None
        equivalentclasses = None
        with db:
            rdftype = {(row[0], row[1]) for row in db.execute(
                    '''SELECT subject, object FROM %s 
                       WHERE (predicate='rdf:type' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}
            subclassof = {(row[0], row[1]) for row in db.execute(
                    '''SELECT subject, object FROM %s 
                       WHERE (predicate='rdfs:subClassOf' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}
            equivalentclasses = {(row[0], row[1]) for row in db.execute(
                    '''SELECT subject, object FROM %s 
                       WHERE (predicate='owl:equivalentClass' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}


        for cc, cp in subclassof:
            parent = onto.setdefault(cp, OntoClass(cp))
            child = onto.setdefault(cc, OntoClass(cc))
            child.parents.add(parent)
            parent.children.add(child)

        for i, c in rdftype:
            onto.setdefault(c, OntoClass(c)).instances.add(i)

        for ec1, ec2 in equivalentclasses:
            equi1 = onto.setdefault(ec1, OntoClass(ec1))
            equi2 = onto.setdefault(ec2, OntoClass(ec2))
            equi1.equivalents.add(equi2)
            equi2.equivalents.add(equi1)


        return onto, rdftype, subclassof, equivalentclasses

    def get_missing_taxonomy_stmts(self, model = DEFAULT_MODEL):

        onto, rdftype, subclassof, equivalentclasses = self.get_onto(self.db, model)

        newrdftype = set()
        newsubclassof = set()
        newequivalentclasses=set()
        
        def addinstance(instance, cls):
            newrdftype.add((instance, cls.name))
            for p in cls.parents:
                addinstance(instance, p)

        def addoverclassof(cls, ocls):
            newsubclassof.add((cls.name, ocls.name))
            ocls.children.add(cls)
            cls.parents.add(ocls)
            for c in frozenset(cls.children):
                addoverclassof(c, cls)
                
        def addsubclassof(scls, cls):
            newsubclassof.add((scls.name, cls.name))
            cls.children.add(scls)
            scls.parents.add(cls)
            for p in frozenset(cls.parents):
                addsubclassof(scls, p)
                
        def addequivalent(cls, equ, memory):
            if equ not in memory:
                memory.add(equ)
                newequivalentclasses.add((cls.name, equ.name))
                cls.equivalents.add(equ)
                equ.equivalents.add(cls)
                for e in frozenset(equ.equivalents):
                    addequivalent(cls, e, memory)

        for name, cls in onto.items():        # just activated onto.items() could be interesting
            for p in frozenset(cls.parents):
                addsubclassof(cls, p)
            for i in cls.instances: 
                addinstance(i, cls)
            
            memory = set()
            for equivalent in frozenset(cls.equivalents):
                addequivalent(cls, equivalent, memory)
            for equivalent in cls.equivalents:
                for p in frozenset(cls.parents):
                    addsubclassof(equivalent, p)
                for c in frozenset(cls.children):
                    addoverclassof(c, equivalent)
                for i in cls.instances:
                    addinstance(i, equivalent)

                
        
        newrdftype -= rdftype
        newsubclassof -= subclassof
        newequivalentclasses -= equivalentclasses
        return newrdftype, newsubclassof, newequivalentclasses

    def symmetric_statements(self, model): # add likelihood

        with self.db:
            stmts = {(row[0], row[1], row[2], model) for row in self.db.execute(
                '''SELECT subject, predicate, object FROM %s 
                WHERE (predicate IN ('%s') AND model=? AND topic='general')
                ''' % (TABLENAME, "', '".join(self.SYMMETRIC_PREDICATES)), [model])}

        return {(o, p, s, m) for s, p, o, m in stmts} - stmts

    def classify(self):


        ok = self.copydb()
        if not ok:
            return

        models = self.get_models()
        newstmts = []

        for model in models:
            rdftype, subclassof, equivalentclasses = self.get_missing_taxonomy_stmts(model)

            newstmts += [(i, "rdf:type", c, model) for i,c in rdftype]
            newstmts += [(cc, "rdfs:subClassOf", cp, model) for cc,cp in subclassof]
            newstmts += [(eq1, "owl:equivalentClass", eq2, model) for eq1,eq2 in equivalentclasses]

            newstmts += self.symmetric_statements(model)


        if newstmts:

            self.update_shared_db(newstmts,'general')
    


    # MUTUAL MODELING methods
    #---------------------------

    def get_mutual_knowledge(self, db):

        visualknowledge = None
        with db:
            visualknowledges = {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT subject, object, model FROM %s WHERE subject!='self' AND subject in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent')) 
                    AND object in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent'))
                    AND predicate="knows" 
                    ''' % (TABLENAME, TABLENAME, TABLENAME))}
            selfknowledges = {(row[0], row[1]) for row in db.execute(
                    '''SELECT subject, model FROM %s WHERE subject!='self' AND subject in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent')) 
                    ''' % (TABLENAME, TABLENAME))}
        
        return visualknowledges, selfknowledges


    def update_models(self):
        
        ok = self.copydb()
        if not ok:
            return
        
        newstmts = []
            
        visualknowledges, selfknowledge = self.get_mutual_knowledge(self.db)
        
        trans_know = {}
        
        for agent, model in selfknowledge:
            
            # the agents are self-conscious :
            #--------------------------------
            spl_model = model.replace('_',' _ ').replace(':',' : ').split()
            
            new_spl_model = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':K_'] + [agent]
            new_model = ''.join(new_spl_model)
            
            generalknowledge = {(row[0], row[1]) for row in self.db.execute(
                        '''SELECT predicate, object FROM %s WHERE subject="%s"
                        AND model="%s" AND topic="general" ''' % (TABLENAME, agent, model))}
            
            newstmts += [('self', 'rdf:type', 'agent', new_model)]
            new_model_mk = trans_know.setdefault((new_model,agent),set())
            new_model_mk.add(('rdf:type','agent'))
            model_mk = trans_know.setdefault((model,agent),set())
            model_mk.add(('rdf:type','agent'))
            
            if generalknowledge:
                for p,o in generalknowledge:
                    newstmts += [('self', p, o, new_model)]
                    new_model_mk = trans_know.setdefault((new_model,agent),set())
                    new_model_mk.add((p,o))
                    model_mk = trans_know.setdefault((model,agent),set())
                    model_mk.add((p,o))
        
        for agent1, agent2, model in visualknowledges:
            
            # take care of the concerned agent2 :
            if agent2=='self':
                agent2 = model.replace('_',' ').split()[-1]
            if agent2==agent1:
                agent2 = 'self'
            
            # agent1 knows agent2 is an agent :
            #----------------------------------
            new_spl_model2 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':K_'] + [agent1]
            new_model2 = ''.join(new_spl_model2)
            
            newstmts += [(agent2, 'rdf:type', 'agent', new_model2)]
            new_model2_mk = trans_know.setdefault((new_model2,agent2),set())
            new_model2_mk.add(('rdf:type','agent'))
            
            k_from_model = trans_know.setdefault((model,agent2),set())
            if k_from_model:
                for p,o in k_from_model:
                    newstmts += [(agent2, p, o, new_model2)]
                    new_model2_mk = trans_know.setdefault((new_model2,agent2),set())
                    new_model2_mk.add((p,o))
            
            # agent1 knows agent2 is self-conscious :
            #-----------------------------------------
            spl_model = model.replace('_',' _ ').replace(':',' : ').split()
            
            new_spl_model1 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':M_'] + [agent1] + [':K_'] + [agent2]
            new_model1 = ''.join(new_spl_model1)
            
                        
            newstmts += [('self', 'rdf:type', 'agent', new_model1)]
            new_model1_mk = trans_know.setdefault((new_model1,agent2),set())
            new_model1_mk.add(('rdf:type','agent'))
            
            k_from_model = trans_know.setdefault((new_model2,agent2),set())
            if k_from_model:
                for p,o in k_from_model:
                    newstmts += [('self', p, o, new_model1)]
                    new_model1_mk = trans_know.setdefault((new_model1,agent2),set())
                    new_model1_mk.add((p,o))
                    
        
        if newstmts:
            
            self.update_shared_db(newstmts,'general')


    # UPDATE methods
    # --------------

    def copydb(self):
    
        try:
            res = self.shareddb.execute("SELECT * FROM %s" % TABLENAME)
            with self.db:
                self.db.execute("DELETE FROM %s" % TABLENAME)
                self.db.executemany('''INSERT INTO %s
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % TABLENAME,
                    res)
            return True
        except sqlite3.OperationalError:
        # can happen if the main application is in the middle of clearing the
        # database (ie, DROP triples)
            return False


    def update_shared_db(self, stmts, topic):
        
        nodes = [[ s, p, o, model, model.replace('_',' ').split()[-1], "%s%s%s%s"%(s,p,o, model), topic ] for s,p,o,model in stmts]

        with self.shareddb:
            self.shareddb.executemany('''INSERT OR IGNORE INTO %s
                 (subject, predicate, object, model, agent, id, topic)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''' % TABLENAME, nodes) 
            self.shareddb.commit()
            
    # LAUNCH methods
    # --------------

    def __call__(self, *args)
        try:
            while self.running:
                time.sleep(1./REASONER_RATE)
                self.classify()
                reason.update_models()
        except KeyboardInterrupt:
            return
            
reason = None

def reasoner_start():
    global reason

    if not reason:
        reason = reasoner()
    reason.running = True
    reason()
    
    

def reasoner_stop():
    global reason
    
    if reason:
        reason.running = False


# TESTING
#-----------------------

if __name__=='__main__':

    reason = reasoner()
    reason.classify()
    reason.update_models()
    reason.shareddb.close()
    reason.db.close()


