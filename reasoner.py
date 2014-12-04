import sqlite3
import Queue

from processkb import DEFAULT_MODEL
from kb import TABLENAME, KBNAME

REASONER_RATE = 5 #Hz

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
            cls.instances.add(instance)
            for p in frozenset(cls.parents):
                addinstance(instance, p)

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

        for name, cls in onto.items():           # for name, cls in onto_active.items()
            for i in frozenset(cls.instances): 
                addinstance(i, cls)
            for p in frozenset(cls.parents):
                addsubclassof(cls, p)
            
            memory = set()
            for equivalent in frozenset(cls.equivalents):
                addequivalent(cls, equivalent, memory)
            for equivalent in cls.equivalents:
                for i in frozenset(cls.instances):
                    addinstance(i, equivalent)
                for p in frozenset(cls.parents):
                    addsubclassof(equivalent, p)

                
        
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

    # ...



    # UPDATE methods
    #-----------------------

    def copydb(self):
    
        try:
            res = self.shareddb.execute("SELECT * FROM %s" % TABLENAME)
            with self.db:
                self.db.execute("DELETE FROM %s" % TABLENAME)
                self.db.executemany('''INSERT INTO %s
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % TABLENAME,
                    res)
            return True
        except sqlite3.OperationalError:
        # can happen if the main application is in the middle of clearing the
        # database (ie, DROP triples)
            return False


    def update_shared_db(self, stmts, topic):
        
        nodes = [[ s, p, o, model, "%s%s%s%s"%(s,p,o, model), topic ] for s,p,o,model in stmts]

        with self.shareddb:
            self.shareddb.executemany('''INSERT OR IGNORE INTO %s
                 (subject, predicate, object, model, id, topic)
                 VALUES (?, ?, ?, ?, ?, ?)''' % TABLENAME, nodes) 
            self.shareddb.commit()

def reasoner_start():
    pass

def reasoner_stop():
    pass


# TESTING
#-----------------------

if __name__=='__main__':

    reason = reasoner()
    reason.classify()
    reason.shareddb.close()
    reason.db.close()


