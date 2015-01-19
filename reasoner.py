import logging; logger = logging.getLogger('mylog');
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import time
from kb import KBNAME, TABLENAME
import kb

REASONER_RATE = 2 #Hz
END = False
DEFAULT_MODEL = 'K_myself'

class OntoClass():

    def __init__(self, name, modified):
        self.name = name
        self.modified = modified
        self.parents = set()
        self.children = set()
        self.instances = set()
        self.equivalents = set()
        
# recursive functions for ontologic inheritances :
#------------------------------------------------

def addequivalent(equivalentclasses, cls, equivalent, llh, memory=None):
    '''
    propagation of equivalence properties :
    --------------------------------------- 
        1) transitivity : (A = B) and (B = C) then (A = C)
        2) symetry : (A = B) then (B = A)
        3) the reflexive property results from symetry and transitivity.
        
    we need to update the classes to make the additions available for the other calls of inheritance functions 
        
    the memory set is used to prevent the method to loop infinitly 
    for instance :
     
        let B in the set of equivalents of A
        then the method do with (A and B) :
        
            1) equivalentclasses.add(A.name , B.name)
            2) A is added to the set of equivalents of B
            3) for every equivalents C of the set of B do the same with (A and C)
                but inside this set we find A (we just added it !)
                so :
                    1) equivalentclasses.add(A.name , A.name) --> ok, reflexivity is added
                    2) B is added to the set of equivalents of A --> (no effect because it was already here, but ok)
                    3) for every equivalents C of the set of A do the same with (A and C)
                        but inside we find B !!!
                        so :
                            without memory, it loops infinitly
                            but with memory, it finds that B have already been handled
    '''
    if not memory:
        memory = set()
    
    if equivalent not in memory:
        if cls.name==equ.name:
            llh=1 # re-find why I did that... 
        
        memory.add(equivalent)
        
        equivalentclasses.append((cls.name, equivalent.name, llh))
        cls.equivalents.add((equivalent, llh)) # update classes
        
        # reflexive property :
        equivalent.equivalents.add((cls, llh)) # update classes
        
        # transitive property :
        for e, llh2 in frozenset(equivalent.equivalents):
            llh3 = max(0.5,min(llh,llh2))
            addequivalent(equivalentclasses, cls, e, llh3, memory)
            

def addsubclassof(subclassof, scls, cls, llh):
    '''
    propagation of inclusions :
    ---------------------------
        the inclusions are just transitives : (A in B) and (B in C) then (A in C)
    
    we need to update the classes to make the additions available for the other calls of inheritance functions
    '''
    subclassof.append((scls.name, cls.name, llh))
    # update classes
    cls.children.add((scls, llh))
    scls.parents.add((cls, llh))
    
    # transitivity :
    for p, llh2 in frozenset(cls.parents):
        llh3 = max(0.5,min(llh,llh2))
        addsubclassof(subclassof, scls, p, llh3)
            

def addoverclassof(subclassof, cls, ocls, llh):
    '''
    back-track propagation of inclusion :
    -------------------------------------
        this backtracking seems to be unusful (it does the same thing than in addsubclassof) 
        but is used after adding equivalences :
        indeed, the property " (A = B) and (C in A) then (C in B) " cannot be taken in account by the method addsubclassof
        
    we need to update the classes to make the additions available for the other calls of inheritance functions
    '''
    
    subclassof.append((cls.name, ocls.name, llh))
    # update classes :
    ocls.children.add((cls, llh))
    cls.parents.add((ocls, llh))
    
    # transitivity :
    for c, llh2 in frozenset(cls.children):
        llh3 = max(0.5,min(llh,llh2))
        addoverclassof(subclassof, c, cls, llh3)
        
        
def addinstance(rdftype, instance, cls, llh):
    '''
    propagation of instances :
    ---------------------------
        the instances are just transitives : (A in B) and (B in C) then (A in C)
        
    don't need to update the classes because they are not used by the other functions
    '''
    
    rdftype.append((instance, cls.name, llh))
    
    for p, llh2 in cls.parents:
        llh3 = max(0.5,min(llh,llh2))
        addinstance(rdftype, instance, p, llh3)
            
#----------------------------------------

class reasoner():

    SYMMETRIC_PREDICATES = {"owl:differentFrom", "owl:sameAs", "owl:disjointWith",'owl:equivalentClass'}

    def __init__(self, database = KBNAME):
        self.db = sqlite3.connect(':memory:')
        self.shareddb = sqlite3.connect(database)
        self.newstmts = []
        

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
            rdftype = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT subject, object, likelihood, modified FROM %s 
                       WHERE (predicate='rdf:type' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}
            subclassof = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT subject, object, likelihood, modified FROM %s 
                       WHERE (predicate='rdfs:subClassOf' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}
            equivalentclasses = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT subject, object, likelihood, modified FROM %s 
                       WHERE (predicate='owl:equivalentClass' AND model=? AND topic='general')
                    ''' % TABLENAME, [model])}


        for cc, cp, llh, pro in subclassof:
            parent = onto.setdefault(cp, OntoClass(cp, pro))
            child = onto.setdefault(cc, OntoClass(cc, pro))
            child.parents.add((parent,llh))
            parent.children.add((child,llh))

        for i, c, llh, pro in rdftype:
            onto.setdefault(c, OntoClass(c, pro)).instances.add((i,llh))

        for ec1, ec2, llh, pro in equivalentclasses:
            equi1 = onto.setdefault(ec1, OntoClass(ec1, pro))
            equi2 = onto.setdefault(ec2, OntoClass(ec2, pro))
            equi1.equivalents.add((equi2,llh))
            equi2.equivalents.add((equi1,llh))


        return onto, rdftype, subclassof, equivalentclasses

    def get_missing_taxonomy_stmts(self, model = DEFAULT_MODEL):

        onto, rdftype, subclassof, equivalentclasses = self.get_onto(self.db, model)

        newrdftype = []
        newsubclassof = []
        newequivalentclasses=[]
        
        for name, cls in onto.items(): # just no-processed onto.items() could be interesting
            if cls.modified:
                for p, llh in frozenset(cls.parents):
                    addsubclassof(newsubclassof, cls, p, llh)
                for i, llh in cls.instances: 
                    addinstance(newrdftype, i, cls, llh)
                
                for equivalent, llh in frozenset(cls.equivalents):
                    addequivalent(newequivalentclasses, cls, equivalent, max(0.5,llh))
                    
                for equivalent, llh in cls.equivalents:
                    if equivalent.name!=cls.name:
                        for p, llh2 in frozenset(cls.parents):
                            llh3 = max(0.5,min(llh,llh2))
                            addsubclassof(newsubclassof, equivalent, p, llh3)
                        for c, llh2 in frozenset(cls.children):
                            llh3 = max(0.5,min(llh,llh2))
                            addoverclassof(newsubclassof, c, equivalent, llh3)
                        for i, llh2 in cls.instances:
                            llh3 = max(0.5,min(llh,llh2))
                            addinstance(newrdftype, i, equivalent, llh3)

        return newrdftype, newsubclassof, newequivalentclasses

    def symmetric_statements(self, model): # add likelihood

        with self.db:
            stmts = {(row[0], row[1], row[2], row[3], model, topic) for row in self.db.execute(
                '''SELECT subject, predicate, object, likelihood, topic FROM %s 
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

        return {(o, p, s, m, llh, topic) for s,p,o,llh,m,topic in stmts}

    def classify(self):

        ok = self.copydb()
        if not ok:
            logging.error('cannot copy the database')
            return

        models = self.get_models()

        for model in models:
            rdftype, subclassof, equivalentclasses = self.get_missing_taxonomy_stmts(model)
            self.newstmts += [(i, "rdf:type", c, model, llh, 'general') for i,c,llh in rdftype]
            self.newstmts += [(cc, "rdfs:subClassOf", cp, model, llh, 'general') for cc,cp,llh in subclassof]
            self.newstmts += [(eq1, "owl:equivalentClass", eq2, model, llh, 'general') for eq1,eq2,llh in equivalentclasses]

            self.newstmts += self.symmetric_statements(model)
    


    # MUTUAL MODELING methods
    #---------------------------

    def get_mutual_knowledge(self, db):

        visualknowledge = None
        with db:
            socialknowledges = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT DISTINCT subject, object, model, likelihood FROM %s WHERE subject!='self' AND subject in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent')) 
                    AND object in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent'))
                    AND predicate="knows" OR predicate = "sees"
                    ''' % (TABLENAME, TABLENAME, TABLENAME))}
            selfknowledges = {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT DISTINCT subject, model, likelihood FROM %s WHERE subject!='self' AND subject in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='agent')) 
                    ''' % (TABLENAME, TABLENAME))}
        
        
        return socialknowledges, selfknowledges


    def update_models(self):
        
        ok = self.copydb()
        if not ok:
            return
            
        socialknowledges, selfknowledge = self.get_mutual_knowledge(self.db)
        
        for agent, model, llh in selfknowledge:
            
            # take care of the concerned agent :
            if agent=='self' or agent == model.replace('_',' ').split()[-1]:
                pass
            else:
            
                # agents are self-conscious :
                #----------------------------
                spl_model = model.replace('_',' _ ').replace(':',' : ').split()
                
                new_spl_model = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':K_'] + [agent]
                new_model = ''.join(new_spl_model)
                
                generalknowledge = {(row[0], row[1], row[2]) for row in self.db.execute(
                            '''SELECT DISTINCT predicate, object, likelihood FROM %s WHERE subject="%s"
                            AND model="%s" AND topic="general" AND modified=1 ''' % (TABLENAME, agent, model))}
                            # not necessary WHERE subject = agent AND model = model, evrerybody are assumed to know 
                            # the general knowledge
                            # general knowledge is ontology stuff (human subclassof agent)
                            # so instences (somebody rdf:Type agent) are specific knowledge 
                            
                specificknowledge = {(row[0], row[1], row[2]) for row in self.db.execute(
                            '''SELECT DISTINCT predicate, object, likelihood FROM %s WHERE subject="%s"
                            AND model="%s" AND topic="specific" AND modified=1 ''' % (TABLENAME, agent, model))}
                            
                    
                self.newstmts += [('self', 'rdf:type', 'agent', new_model, llh, 'general')]
                
                # transfert of knowledgde :
                #--------------------------
                if generalknowledge: # things that the robot assums known for every body
                    for p,o,lh in generalknowledge:
                        
                        if o=='self':
                            o = model.replace('_',' ').split()[-1]
                        if o==agent:
                            o = 'self'
                        
                        if llh > 0.5:
                            self.newstmts += [('self', p, o, new_model, lh, 'general')]
                        else:
                            self.newstmts += [('self', p, o, new_model, 0.5, 'general')]
                        
                if specificknowledge: # agents know the specific things about themself
                    for p,o,lh in specificknowledge:
                        
                        if o=='self':
                            o = model.replace('_',' ').split()[-1]
                        if o==agent:
                            o = 'self'
                    
                        if llh > 0.5:
                            self.newstmts += [('self', p, o, new_model, lh, 'specific')]
                        else:
                            self.newstmts += [('self', p, o, new_model, 0.5, 'specific')]
                        
        
        for agent1, agent2, model, llh in socialknowledges:
            
            spl_model = model.replace('_',' _ ').replace(':',' : ').split()
            
            if agent1==model.replace('_',' ').split()[-1] or agent1=='self':
                pass
            else:
            
                # take care of the concerned agent2 :
                if agent2=='self':
                    agent2 = model.replace('_',' ').split()[-1]
                if agent2==agent1:
                    agent2 = 'self'
            
                # agent1 knows agent2 is an agent :
                #----------------------------------
                new_spl_model2 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':K_'] + [agent1]
                new_model2 = ''.join(new_spl_model2)
                
                self.newstmts += [(agent2, 'rdf:type', 'agent', new_model2, llh, 'general')]
                
                # agent1 knows agent2 is self-conscious : 
                #----------------------------------------
                if agent2=='self':
                    pass
                else:
                    spl_model = model.replace('_',' _ ').replace(':',' : ').split()
                    
                    new_spl_model1 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':M_'] + [agent1] + [':K_'] + [agent2]
                    new_model1 = ''.join(new_spl_model1)
                    
                                
                    self.newstmts += [('self', 'rdf:type', 'agent', new_model1, llh, 'general')]
                            
                # the modeler knows that agent1 and agent2 are agents :
                #------------------------------------------------------
                self.newstmts += [(agent1, 'rdf:type', 'agent', model, llh, 'general')]
                self.newstmts += [(agent2, 'rdf:type', 'agent', model, llh, 'general')]


    # UPDATE methods
    # --------------

    def copydb(self):
    
        try:
            res = self.shareddb.execute("SELECT * FROM %s" % TABLENAME)
            with self.db:
                self.db.execute("DELETE FROM %s" % TABLENAME)
                self.db.executemany('''INSERT INTO %s
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % TABLENAME,
                    res)
            return True
        except sqlite3.OperationalError:
        # can happen if the main application is in the middle of clearing the
        # database (ie, DROP triples)
            return False


    def update_shared_db(self):
        
        while True:
            try:
                self.shareddb.execute('''SELECT * FROM %s''' % TABLENAME)
                break
            except sqlite3.OperationalError:
                pass
        
        if len(self.newstmts)<6:
            print('stmts < 6 !!!')
        nodes = [[ s, p, o, model, model.replace('_',' ').split()[-1], "%s%s%s%s"%(s,p,o, model), topic ] for s,p,o,model,llh,topic in self.newstmts]
        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o,model,llh,topic in self.newstmts]
        llh_nodes = [[ llh, "%s%s%s%s"%(s,p,o, model) ] for s,p,o,model,llh,topic in self.newstmts]

        #with self.shareddb:
        #-------------------
        
        # the process are finished
        self.shareddb.execute(''' UPDATE %s SET modified=0 
                      WHERE modified=1''' % TABLENAME)
        
        self.shareddb.executemany('''INSERT OR IGNORE INTO %s
             (subject, predicate, object, model, agent, id, topic)
             VALUES (?, ?, ?, ?, ?, ?, ?)''' % TABLENAME, nodes) 
        self.shareddb.executemany('''UPDATE %s SET infered=1 WHERE id=?''' % TABLENAME, ids)
        # after this, all the infered nodes (reached by reason) are set with 'infered'=1 (default value)
        
        # update the likelihood just for the infered nodes
        
        for llh, node in llh_nodes:
            cur = self.shareddb.execute('''SELECT likelihood FROM %s WHERE id=? '''% TABLENAME, [node])
            lh = cur.fetchone()[0]
            likelihood = llh
            if (lh-llh)*(lh-llh)==1:
                pass
            else:
                likelihood = lh*llh/( lh*llh + (1-lh)*(1-llh) )
            self.shareddb.execute(''' UPDATE %s SET likelihood=%f
                                WHERE id=? AND infered=1''' % (TABLENAME, likelihood), [node])
            # not so easy :
            #self.shareddb.execute(''' UPDATE %s SET modified=1
            #                    WHERE id=? AND infered=1''' % (TABLENAME), [node])
                      
        # then inference is done, so 'infered'=0 for all nodes
        self.shareddb.execute(''' UPDATE %s SET infered=0 
                      WHERE infered=1''' % TABLENAME)
                      
        # self_recognition :
        #self.shareddb.execute('''UPDATE %s SET object="self" WHERE object=(SELECT agent)''' % TABLENAME)
        #self.shareddb.execute('''UPDATE %s SET subject="self" WHERE subject=(SELECT agent)''' % TABLENAME)
        
        self.shareddb.commit()
        
        self.newstmts = []
        
        
            
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
                self.update_models()
                self.update_shared_db()
                
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


