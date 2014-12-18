import logging; logger = logging.getLogger('mylog');
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import time
from kb import KBNAME, TABLENAME
import kb

REASONER_RATE = 2 #Hz
END = False
DEFAULT_MODEL = 'K_myself'

# add M operator et K operator

class OntoClass():

    def __init__(self, name):
        self.name = name
        self.parents = set()
        self.children = set()
        self.instances = set()
        self.equivalents = set()

class reasoner():

    SYMMETRIC_PREDICATES = {"owl:differentFrom", "owl:sameAs", "owl:disjointWith",'owl:equivalentClass'}

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
            rdftype = {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT subject, object, likelihood FROM %s 
                       WHERE (predicate='rdf:type' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}
            subclassof = {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT subject, object, likelihood FROM %s 
                       WHERE (predicate='rdfs:subClassOf' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}
            equivalentclasses = {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT subject, object, likelihood FROM %s 
                       WHERE (predicate='owl:equivalentClass' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}


        for cc, cp, llh in subclassof:
            parent = onto.setdefault(cp, OntoClass(cp))
            child = onto.setdefault(cc, OntoClass(cc))
            child.parents.add((parent,llh))
            parent.children.add((child,llh))

        for i, c, llh in rdftype:
            onto.setdefault(c, OntoClass(c)).instances.add((i,llh))

        for ec1, ec2, llh in equivalentclasses:
            equi1 = onto.setdefault(ec1, OntoClass(ec1))
            equi2 = onto.setdefault(ec2, OntoClass(ec2))
            equi1.equivalents.add((equi2,llh))
            equi2.equivalents.add((equi1,llh))


        return onto, rdftype, subclassof, equivalentclasses

    def get_missing_taxonomy_stmts(self, model = DEFAULT_MODEL):

        onto, rdftype, subclassof, equivalentclasses = self.get_onto(self.db, model)

        newrdftype = []
        newsubclassof = []
        newequivalentclasses=[]
        
        def addinstance(instance, cls, llh):
            newrdftype.append((instance, cls.name, llh))
            for p, llh2 in cls.parents:
                llh3 = max(0.5,min(llh,llh2))
                addinstance(instance, p, llh3)

        def addoverclassof(cls, ocls, llh):
            newsubclassof.append((cls.name, ocls.name, llh))
            ocls.children.add((cls, llh))
            cls.parents.add((ocls, llh))
            for c, llh2 in frozenset(cls.children):
                llh3 = max(0.5,min(llh,llh2))
                addoverclassof(c, cls, llh3)
                
        def addsubclassof(scls, cls, llh):
            newsubclassof.append((scls.name, cls.name, llh))
            cls.children.add((scls, llh))
            scls.parents.add((cls, llh))
            for p, llh2 in frozenset(cls.parents):
                llh3 = max(0.5,min(llh,llh2))
                addsubclassof(scls, p, llh3)
                
        def addequivalent(cls, equ, llh, memory):
            if equ not in memory:
                if cls.name==equ.name:
                    llh=1
                memory.add(equ) # check if need to add llh
                newequivalentclasses.append((cls.name, equ.name, llh))
                cls.equivalents.add((equ, llh))
                equ.equivalents.add((cls, llh))
                for e, llh2 in frozenset(equ.equivalents):
                    llh3 = max(0.5,min(llh,llh2))
                    addequivalent(cls, e, llh3, memory)

        for name, cls in onto.items():        # just activated onto.items() could be interesting
            for p, llh in frozenset(cls.parents):
                addsubclassof(cls, p, llh)
            for i, llh in cls.instances: 
                addinstance(i, cls, llh)
            
            memory = set()
            for equivalent, llh in frozenset(cls.equivalents):
                addequivalent(cls, equivalent, max(0.5,llh), memory)
            for equivalent, llh in cls.equivalents:
                if equivalent.name!=cls.name:
                    for p, llh2 in frozenset(cls.parents):
                        llh3 = max(0.5,min(llh,llh2))
                        addsubclassof(equivalent, p, llh3)
                    for c, llh2 in frozenset(cls.children):
                        llh3 = max(0.5,min(llh,llh2))
                        addoverclassof(c, equivalent, llh3)
                    for i, llh2 in cls.instances:
                        llh3 = max(0.5,min(llh,llh2))
                        addinstance(i, equivalent, llh3)

        return newrdftype, newsubclassof, newequivalentclasses

    def symmetric_statements(self, model): # add likelihood

        with self.db:
            stmts = {(row[0], row[1], row[2], row[3], model) for row in self.db.execute(
                '''SELECT subject, predicate, object, likelihood FROM %s 
                WHERE (predicate IN ('%s') AND model=? AND topic='general')
                ''' % (TABLENAME, "', '".join(self.SYMMETRIC_PREDICATES)), [model])}
                
                # the fact that we can use llh and not max(0.5,llh) come frome 
                # that the contrary is also symetrique
                # with a motor of contrary it will be done automatically
                # then we could proprely use max(0.5,llh)
                #
                # demo :
                # a=b false => b=a ? (can't say)
                # but by contrary stmt :
                # a!=b true => b!=a true
                # then by contrary stmt again :
                # b=a false

        return {(o, p, s, m, llh) for s, p, o, llh, m in stmts}

    def classify(self):

        ok = self.copydb()
        if not ok:
            logging.error('cannot copy the database')
            return

        models = self.get_models()
        newstmts = []

        for model in models:
            rdftype, subclassof, equivalentclasses = self.get_missing_taxonomy_stmts(model)
            newstmts += [(i, "rdf:type", c, model, llh) for i,c,llh in rdftype]
            newstmts += [(cc, "rdfs:subClassOf", cp, model, llh) for cc,cp,llh in subclassof]
            newstmts += [(eq1, "owl:equivalentClass", eq2, model, llh) for eq1,eq2,llh in equivalentclasses]

            newstmts += self.symmetric_statements(model)


        if newstmts:

            self.update_shared_db(newstmts,'general')
    


    # MUTUAL MODELING methods
    #---------------------------

    def get_mutual_knowledge(self, db):

        visualknowledge = None
        with db:
            socialknowledges = {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT subject, object, model FROM %s WHERE subject!='self' AND subject in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent')) 
                    AND object in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent'))
                    AND predicate="knows" 
                    ''' % (TABLENAME, TABLENAME, TABLENAME))}
            selfknowledges = {(row[0], row[1]) for row in db.execute(
                    '''SELECT subject, model FROM %s WHERE subject!='self' AND subject in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent')) 
                    AND model='%s'
                    ''' % (TABLENAME, TABLENAME, DEFAULT_MODEL))}
        
        return socialknowledges, selfknowledges


    def update_models(self):
        
        ok = self.copydb()
        if not ok:
            return
        
        newstmts = []
            
        socialknowledges, selfknowledge = self.get_mutual_knowledge(self.db)
        
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
        
        for agent1, agent2, model in socialknowledges:
            
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % TABLENAME,
                    res)
            return True
        except sqlite3.OperationalError:
        # can happen if the main application is in the middle of clearing the
        # database (ie, DROP triples)
            return False


    def update_shared_db(self, stmts, topic):
        
        nodes = [[ s, p, o, model, model.replace('_',' ').split()[-1], "%s%s%s%s"%(s,p,o, model), topic ] for s,p,o,model,llh in stmts]
        llh_nodes = [[ llh, llh, llh, "%s%s%s%s"%(s,p,o, model) ] for s,p,o,model,llh in stmts]

        #with self.shareddb:
        self.shareddb.executemany('''INSERT OR IGNORE INTO %s
             (subject, predicate, object, model, agent, id, topic)
             VALUES (?, ?, ?, ?, ?, ?, ?)''' % TABLENAME, nodes) 
        
        self.shareddb.executemany(''' UPDATE %s SET likelihood = ((SELECT likelihood)*?
                      /((SELECT likelihood)*? + (1-(SELECT likelihood))*(1-?))) 
                      WHERE id=? AND infered=1''' % TABLENAME, llh_nodes)
                      
        self.shareddb.execute(''' UPDATE %s SET infered=0 
                      WHERE infered=1''' % TABLENAME)
        
        self.shareddb.commit()
        
        
            
    # LAUNCH methods
    # --------------

    def __call__(self, *args):
        try:
            logger.info('reasonner starts')
            while self.running:
                time.sleep(1./REASONER_RATE)
                
                while True:
                    try:
                        self.shareddb.execute('''SELECT * FROM %s''' % TABLENAME)
                        break
                    except sqlite3.OperationalError:
                        pass
                        
                self.classify()
                reason.update_models()
                print('--------------------reasoning done')
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


