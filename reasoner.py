'''this code performs ontological reasoning and mutual modeling inference
from a knowledge base and update it with this infered knowledge'''

import logging
LOGGER = logging.getLogger('mylog')
DEBUG_LEVEL = logging.DEBUG

import sqlite3
import time
from kb import KBNAME, TABLENAME

REASONER_RATE = 2 #Hz
END = False
DEFAULT_MODEL = 'K_myself'
MUTUAL_MODELING_ORDER = 5


# usefull objects :
#==================

class OntoClass():
    ''' this class defines an object that encodes ontologic links
    between existing subjects/objects in the knowledge base'''
    def __init__(self, name, processed):
        self.name = name
        self.processed = processed
        self.parents = set()
        self.children = set()
        self.instances = set()
        self.equivalents = set()

# recursive functions for ontologic inheritances :
#=================================================

def addproperties(name, active_properties, passive_properties, llh1, newproperties):
    '''for inheritance of non-ontologic properties'''
    for p,o,llh2 in active_properties:
        newproperties.append((name, p, o, max(0.5, min(llh1,llh2))))
    for s,p,llh2 in passive_properties:
        newproperties.append((s, p, name, max(0.5, min(llh1,llh2))))

def addequivalent(equivalentclasses, cls, equivalent, llh, active_properties, passive_properties, newproperties, memory=None ):
    '''
    propagation of equivalence properties :
    ---------------------------------------
        1) transitivity : (A = B) and (B = C) then (A = C)
        2) symetry : (A = B) then (B = A)
        3) the reflexive property results from symetry and transitivity.

    we need to update the classes to make the additions available
    for the other calls of inheritance functions

    the memory set is used to prevent the method to loop infinitly
    for instance :

        let B in the set of equivalents of A
        then the method do with (A and B) :

            1) equivalentclasses.add(A.name , B.name)
            2) A is added to the set of equivalents of B
            3) for every equivalents C of the set of B do the same
               with (A and C) but inside this set we find A (we just added it !)
                so :
                    1) equivalentclasses.add(A.name , A.name)
                       --> ok, reflexivity is added
                    2) B is added to the set of equivalents of A
                       --> (no effect because it was already here, but ok)
                    3) for every equivalents C of the set of A
                       do the same with (A and C)...
                       but inside we find B !!!
                        so :
                            without memory, it loops infinitly
                            but with memory, it finds that
                            B have already been handled
    '''
    if not memory:
        memory = set()

    if equivalent not in memory:
        if cls.name == equivalent.name:
            llh = 1 # need to remind why did I do that...

        memory.add(equivalent)

        equivalentclasses.append((cls.name, equivalent.name, llh))
        cls.equivalents.add((equivalent, llh)) # update classes

        addproperties(equivalent.name, active_properties, passive_properties, llh, newproperties)

        # reflexive property :
        equivalent.equivalents.add((cls, llh)) # update classes

        # transitive property :
        for equ, llh2 in frozenset(equivalent.equivalents):
            llh3 = max(0.5, min(llh, llh2))
            addequivalent(equivalentclasses, cls, equ, llh3, active_properties, passive_properties, newproperties, memory)


def addsubclassof(subclassof, scls, cls, llh, active_properties, passive_properties, newproperties):
    '''
    propagation of inclusions :
    ---------------------------
        the inclusions are just transitives :
        (A in B) and (B in C) then (A in C)

    we need to update the classes to make the additions available
    for the other calls of inheritance functions
    '''
    subclassof.append((scls.name, cls.name, llh))
    # update classes
    cls.children.add((scls, llh))
    scls.parents.add((cls, llh))

    # no (non-ontologic)properties inheritance from child to parents...

    # transitivity :
    for p, llh2 in frozenset(cls.parents):
        llh3 = max(0.5,min(llh,llh2))
        addsubclassof(subclassof, scls, p, llh3, active_properties, passive_properties, newproperties)


def addoverclassof(subclassof, cls, ocls, llh, active_properties, passive_properties, newproperties):
    '''
    back-track propagation of inclusion :
    -------------------------------------
        this backtracking seems to be unusful
        (it does the same thing than in addsubclassof)
        but is used after adding equivalences :
        indeed, the property " (A = B) and (C in A) then (C in B) "
        cannot be taken in account by the method addsubclassof

    we need to update the classes to make the additions available
    for the other calls of inheritance functions
    '''

    subclassof.append((cls.name, ocls.name, llh))
    # update classes :
    ocls.children.add((cls, llh))
    cls.parents.add((ocls, llh))

    addproperties(cls.name, active_properties, passive_properties, llh, newproperties)

    # transitivity :
    for child, llh2 in frozenset(cls.children):
        llh3 = max(0.5, min(llh, llh2))
        addoverclassof(subclassof, child, cls, llh3, active_properties, passive_properties, newproperties)


def addinstance(rdftype, instance, cls, llh, active_properties, passive_properties, newproperties):
    '''
    propagation of instances :
    ---------------------------
        the instances are just transitives :
        (A in B) and (B in C) then (A in C)

    don't need to update the classes because
    they are not used by the other functions
    '''

    rdftype.append((instance, cls.name, llh))

    # no (non-ontologic)properties inheritance from instance to classes...

    for par, llh2 in cls.parents:
        llh3 = max(0.5, min(llh, llh2))
        addinstance(rdftype, instance, par, llh3, active_properties, passive_properties, newproperties)

# REASONER :
#===========

class Reasoner():

    # ontologic keywords :
    SYMMETRIC_PREDICATES = {"owl:differentFrom", "owl:sameAs", "owl:disjointWith", 'owl:equivalentClass'}
    INHERITANCE_PREDICATES = {"rdfs:subClassOf"}
    OCCURENCE_PREDICATES = {"rdf:type"}
    EQUIVALENC_PREDICATES = {"owl:equivalentClass"}
    ONTOLOGIC_PREDICATES = SYMMETRIC_PREDICATES|INHERITANCE_PREDICATES|OCCURENCE_PREDICATES|EQUIVALENC_PREDICATES

    # mutual modeling keywords :
    VISUAL_KNOWLEDGE_PREDICATES = {"sees","imagines","looks"} # imply a visual knowledge of the object
    GENERAL_KNOWLEDGE_PREDICATES = {"knows", "conceives", "fears", "loves", "likes", "prefers", "dislies", "hates"} # imply a general knowledge of the object
    VISIBLE_PREDICATES = {"sees", "looks", "fears", "is", "shows", "dances", "says", "sings", "smiles_to", "smiles"} # given by visual knowledge
    OBTAINABLE_GENERAL_PREDICATES = {"knows", "conceives", "fears", "loves", "likes", "prefers", "dislikes", "hates"}|ONTOLOGIC_PREDICATES # given by general knowledge

    # contrary conflict keywords :
    CONTRARIES = {("equals","differs"), ("owl:differentFrom","owl:sameAs"), ('owl:equivalentClass','owl:differentClass'),
                             ("owl:disjointWith","owl:jointWith"), ('likes','dislikes'), ('loves','hates') } # 
    NEGATIONS = {"dont_",'doesnt_','cannot_'} # imply existence of the node with 1-llh
    CONFIRMATIONS = {'do_'} # imply existence of the node with the same llh
    POSSIBILITIES = {'can_','could_'} # imply existence of the node, but with llh = 0.5
    ABSOLUTE_RESTRICTIONS = {"looks":{'looks','sees'},'imagines':{'imagines','sees'}} # restriction with all possible objects
    RELATIVES_RESTRICTIONS = {"prefers":{"prefers"} } # restriction just with the other objects of the same class

    def __init__(self, database=KBNAME):
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


    # ONTOLOGY methods :
    #===================

    def get_onto(self, db, model = DEFAULT_MODEL):

        onto = {}

        rdftype = None
        subclassof = None
        equivalentclasses = None
        with db:
            rdftype = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT subject, object, trust, modified FROM %s 
                       WHERE (predicate='rdf:type' AND model=?)
                    ''' % TABLENAME, [model])}
            subclassof = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT subject, object, trust, modified FROM %s
                       WHERE (predicate='rdfs:subClassOf' AND model=?)
                    ''' % TABLENAME, [model])}
            equivalentclasses = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT subject, object, trust, modified FROM %s
                       WHERE (predicate='owl:equivalentClass' AND model=?)
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
        newproperties = []

        for name, cls in onto.items(): # just no-processed onto.items() could be interesting
            if not cls.processed :

                # get all NON ONTOLOGIC !!!!! properies of the class:
                active_properties = {(row[0], row[1], row[2]) for row in self.db.execute(
                                    '''SELECT predicate, object, trust FROM %s
                                    WHERE subject="%s" AND model="%s" AND predicate NOT IN ('%s')'''
                                    % (TABLENAME, name, model,"', '".join(self.ONTOLOGIC_PREDICATES)))}

                passive_properties = {(row[0], row[1], row[2]) for row in self.db.execute(
                                    '''SELECT subject, predicate, trust FROM %s
                                    WHERE object="%s" AND model="%s" AND predicate NOT IN ('%s')'''
                                    % (TABLENAME, name, model,"', '".join(self.ONTOLOGIC_PREDICATES)))}


                for p, llh in frozenset(cls.parents):
                    addsubclassof(newsubclassof, cls, p, llh, active_properties, passive_properties, newproperties)
                for i, llh in cls.instances:
                    addproperties(i, active_properties, passive_properties, llh, newproperties)
                    addinstance(newrdftype, i, cls, llh, active_properties, passive_properties, newproperties)
                for c, llh in cls.children:
                    addproperties(c.name, active_properties, passive_properties, llh, newproperties)

                for equivalent, llh in frozenset(cls.equivalents):
                    addequivalent(newequivalentclasses, cls, equivalent, max(0.5,llh), active_properties, passive_properties, newproperties)

                for equivalent, llh in cls.equivalents:
                    if equivalent.name!=cls.name:
                        for p, llh2 in frozenset(cls.parents):
                            llh3 = max(0.5,min(llh,llh2))
                            addsubclassof(newsubclassof, equivalent, p, llh3, active_properties, passive_properties, newproperties)
                        for c, llh2 in frozenset(cls.children):
                            llh3 = max(0.5,min(llh,llh2))
                            addoverclassof(newsubclassof, c, equivalent, llh3, active_properties, passive_properties, newproperties)
                        for i, llh2 in cls.instances:
                            llh3 = max(0.5,min(llh,llh2))
                            addinstance(newrdftype, i, equivalent, llh3, active_properties, passive_properties, newproperties)

        return newrdftype, newsubclassof, newequivalentclasses, newproperties

    def symmetric_statements(self, model): # add trust

        with self.db:
            stmts = {(row[0], row[1], row[2], row[3]) for row in self.db.execute(
                '''SELECT subject, predicate, object, trust FROM %s 
                WHERE (predicate IN ('%s') AND model=?)
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

        return {(o, p, s, model, llh) for s,p,o,llh in stmts}

    def classify(self):

        ok = self.copydb()
        if not ok:
            logging.error('cannot copy the database')
            return

        models = self.get_models()

        for model in models:
            rdftype, subclassof, equivalentclasses, inheritedproperties = self.get_missing_taxonomy_stmts(model)
            self.newstmts += [(i, "rdf:type", c, model, llh) for i,c,llh in rdftype]
            self.newstmts += [(cc, "rdfs:subClassOf", cp, model, llh) for cc,cp,llh in subclassof]
            self.newstmts += [(eq1, "owl:equivalentClass", eq2, model, llh) for eq1,eq2,llh in equivalentclasses]
            self.newstmts += [(s, p, o, model, llh) for s,p,o,llh in inheritedproperties]
            self.newstmts += self.symmetric_statements(model)



    # MUTUAL MODELING methods :
    #==========================

    def get_mutual_modelings(self, db):

        with db:
            generalModelings = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT DISTINCT subject, object, model, trust FROM %s WHERE subject!='self' AND subject in
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='Agent'))
                    AND object in
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='Agent'))
                    AND predicate IN ('%s')
                    AND trust>=0.5
                    ''' % (TABLENAME, TABLENAME, TABLENAME, "', '".join(self.GENERAL_KNOWLEDGE_PREDICATES)))}

            visualModelings = {(row[0], row[1], row[2], row[3]) for row in db.execute(
                    '''SELECT DISTINCT subject, object, model, trust FROM %s WHERE subject!='self' AND subject in
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='Agent'))
                    AND object in
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='Agent'))
                    AND predicate IN ('%s')
                    AND trust>=0.5
                    ''' % (TABLENAME, TABLENAME, TABLENAME, "', '".join(self.VISUAL_KNOWLEDGE_PREDICATES)))}

            selfModelings = {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT DISTINCT subject, model, trust FROM %s WHERE subject!='self' AND subject in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='Agent'))
                    ''' % (TABLENAME, TABLENAME))} | {(row[0], row[1], row[2]) for row in db.execute(
                    '''SELECT DISTINCT object, model, trust FROM %s WHERE object!='self' AND object in 
                    (SELECT subject FROM %s WHERE (predicate='rdf:type' AND  object='Agent'))
                    ''' % (TABLENAME, TABLENAME))}

        return generalModelings, visualModelings, selfModelings


    def update_models(self):

        ok = self.copydb()
        if not ok:
            return

        generalModelings, visualModelings, selfModelings = self.get_mutual_modelings(self.db)

        for agent, model, llh in selfModelings:
        # when there is an agent

            # take care of who is the agent :
            #--------------------------------
            # if the agent is already the agent of the model,
            # dont need to create a new model for himself
            # because it already exists
            if agent=='self' or agent == model.replace('_',' ').split()[-1]:
                # model.replace('_',' ').split()[-1] gives the agent of the model
                pass

            # dont pass the mutual modeling level (to not add infinite models):
            #------------------------------------------------------------------
            elif len(model.replace(':',' ').split())>MUTUAL_MODELING_ORDER:
                pass

            else:

                # get the name of the model for the agent :
                #------------------------------------------
                spl_model = model.replace('_',' _ ').replace(':',' : ').split()
                new_spl_model = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':K_'] + [agent]
                new_model = ''.join(new_spl_model)

                # get the knowledge that the agent is supposed to have:
                #------------------------------------------------------
                common_ground = {(row[0], row[1], row[2], row[3]) for row in self.db.execute(
                            '''SELECT DISTINCT subject, predicate, object, trust FROM %s
                            WHERE ( id IN (
                            SELECT DISTINCT subject WHERE predicate='is'
                                                    AND object='common'
                                                    AND model='%s'
                                                    AND trust>=0.5)
                            OR (predicate='is' AND object='common' AND trust>=0.5) )
                            ''' % (TABLENAME, model))}
                            #AND  modified=1''' % (TABLENAME, model))}

                shared_ground = {(row[0], row[1], row[2], row[3]) for row in self.db.execute(
                            '''SELECT DISTINCT subject, predicate, object, trust FROM %s
                            WHERE id IN (
                            SELECT DISTINCT subject WHERE predicate='is'
                                                    AND object='shared'
                                                    AND model='%s'
                                                    AND trust>=0.5)
                            ''' % (TABLENAME, model))}
                            #AND  modified=1 ''' % (TABLENAME, model))}

                self_description = {(row[0], row[1], row[2]) for row in self.db.execute(
                            '''SELECT DISTINCT predicate, object, trust FROM %s WHERE subject="%s"
                            AND model="%s" ''' % (TABLENAME, agent, model))}
                            #AND modified=1 ''' % (TABLENAME, agent, model))}

                # make sure agent is conscious to be an agent :
                #----------------------------------------------
                self.newstmts += [(agent, 'rdf:type', 'Agent', new_model, llh)]

                # instill in the agent his supposed knowledge :
                #----------------------------------------------
                if common_ground:
                # things that the robot assums that they are known for everybody
                # and that everybody knows that they are known for everybody
                    for s,p,o,lh in common_ground:

                        if o=='self':
                            o = model.replace('_',' ').split()[-1]
                        #if o==agent:
                        #    o = 'self'

                        if llh > 0.5:
                            self.newstmts += [(s, p, o, new_model, lh)]
                        else:
                            self.newstmts += [(s, p, o, new_model, 0.5)]

                if shared_ground:
                # things that the robot just assums that they are known for every body
                    for s,p,o,lh in shared_ground:

                        if o=='self':
                            o = model.replace('_',' ').split()[-1]
                        #if o==agent:
                        #    o = 'self'

                        if llh > 0.5:
                            self.newstmts += [(s, p, o, new_model, lh)]
                        else:
                            self.newstmts += [(s, p, o, new_model, 0.5)]

                if self_description:
                # the modeled agent is supposed to know the information about himself
                    for p,o,lh in self_description:

                        if o=='self':
                            o = model.replace('_',' ').split()[-1]
                        #if o==agent:
                        #    o = 'self'

                        if llh > 0.5:
                            self.newstmts += [(agent, p, o, new_model, lh)]
                        else:
                            self.newstmts += [(agent, p, o, new_model, 0.5)]

                # the modeler knows that the agent is an agent:
                #----------------------------------------------
                self.newstmts += [(agent, 'rdf:type', 'Agent', model, llh)]


        for agent1, agent2, model, llh in visualModelings:
        # when there are 2 agents, and agent1 visualizes agent2

            # take care of who is agent1 :
            #-----------------------------
            # if the agent1 is already the agent of the model,
            # dont need to create a new model for himself
            # because it already exists
            if agent1==model.replace('_',' ').split()[-1] or agent1=='self':
                pass
            else:

                # take care of who is agent2 :
                #-----------------------------
                # agent2 could be the agent of the model or agent1
                if agent2=='self':
                    agent2 = model.replace('_',' ').split()[-1]
                #if agent2==agent1:
                #    agent2 = 'self'

                # get the name of the model for agent1 :
                #---------------------------------------
                spl_model = model.replace('_',' _ ').replace(':',' : ').split()
                new_spl_model2 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':K_'] + [agent1]
                new_model2 = ''.join(new_spl_model2)

                # agent1 knows agent2 is an agent :
                #----------------------------------
                self.newstmts += [(agent2, 'rdf:type', 'Agent', new_model2, llh)]

                # get the name of the model for agent2 modeled by agent1:
                #--------------------------------------------------------
                if agent2=='self':
                    # agent1 doesn't need a model for itself
                    # we've just created it
                    pass
                else:
                    spl_model = model.replace('_',' _ ').replace(':',' : ').split()
                    new_spl_model1 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':M_'] + [agent1] + [':K_'] + [agent2]
                    new_model1 = ''.join(new_spl_model1)

                    # agent1 knows agent2 knows it is itself an agent:
                    #-------------------------------------------------
                    self.newstmts += [(agent2, 'rdf:type', 'Agent', new_model1, llh)]

                    # transfere to agent1 VISIBLE information about agent2:
                    #------------------------------------------------------
                    visible_ground = {(row[0], row[1], row[2], row[3]) for row in self.db.execute(
                            '''SELECT DISTINCT subject, predicate, object, trust FROM %s
                            WHERE (subject = '%s'AND model = '%s' AND (
                            id IN (
                            SELECT DISTINCT subject FROM %s WHERE predicate='is'
                                                    AND object='visible'
                                                    AND trust>=0.5)
                            OR (predicate IN ('%s') and trust>=0.5)))
                            OR (subject IN (
                            SELECT id FROM %s WHERE subject='%s') AND predicate='is' AND object='visible' and trust>=0.5)
                            ''' % (TABLENAME, agent2, model, TABLENAME, "', '".join(self.VISIBLE_PREDICATES), TABLENAME, agent2))}

                    # si neud dy type "predicat is visible -> ajouter predicat aux visible_predicats

                    # instill in agent1 his supposed knowledge about agent2 :
                    #--------------------------------------------------------
                    if visible_ground:
                    # things about agent2 that the robot assums that is known by agent1 because of
                    # the visibility of the agent2
                        for s,p,o,lh in visible_ground:

                            if o=='self':
                                o = model.replace('_',' ').split()[-1]
                            #if o==agent1:
                            #    o = 'self'

                            if llh > 0.5:
                                self.newstmts += [(s, p, o, new_model, lh)]
                            else:
                                self.newstmts += [(s, p, o, new_model, 0.5)] 


                # the modeler knows that agent1 and agent2 are agents :
                #------------------------------------------------------
                self.newstmts += [(agent1, 'rdf:type', 'Agent', model, llh)]
                self.newstmts += [(agent2, 'rdf:type', 'Agent', model, llh)]


        for agent1, agent2, model, llh in generalModelings:
        # when there are 2 agents, and agent1 knows general info about agent2

            # take care of who is agent1 :
            #-----------------------------
            # if the agent1 is already the agent of the model,
            # dont need to create a new model for himself
            # because it already exists
            if agent1==model.replace('_',' ').split()[-1] or agent1=='self':
                pass
            else:

                # take care of who is agent2 :
                #-----------------------------
                # agent2 could be the agent of the model or agent1
                if agent2=='self':
                    agent2 = model.replace('_',' ').split()[-1]
                #if agent2==agent1:
                #    agent2 = 'self'

                # get the name of the model for agent1 :
                #---------------------------------------
                spl_model = model.replace('_',' _ ').replace(':',' : ').split()
                new_spl_model2 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':K_'] + [agent1]
                new_model2 = ''.join(new_spl_model2)

                # agent1 knows agent2 is an agent :
                #----------------------------------
                self.newstmts += [(agent2, 'rdf:type', 'Agent', new_model2, llh)]

                # get the name of the model for agent2 modeled by agent1:
                #--------------------------------------------------------
                if agent2=='self':
                    # agent1 doesn't need a model for itself
                    # we've just created it
                    pass
                else:
                    spl_model = model.replace('_',' _ ').replace(':',' : ').split()
                    new_spl_model1 = [''.join(spl_model[:-3])] + ['M_'] + [''.join(spl_model[-1])] + [':M_'] + [agent1] + [':K_'] + [agent2]
                    new_model1 = ''.join(new_spl_model1)

                    # agent1 knows agent2 knows it is itself an agent:
                    #-------------------------------------------------
                    self.newstmts += [(agent2, 'rdf:type', 'Agent', new_model1, llh)]


                    # transfere to agent1 VISIBLE information about agent2:
                    #------------------------------------------------------
                    obtainable_ground = {(row[0], row[1], row[2], row[3]) for row in self.db.execute(
                            '''SELECT DISTINCT subject, predicate, object, trust FROM %s
                            WHERE (subject = '%s'AND model = '%s'
                            AND predicate IN ('%s') and trust>=0.5
                            ''' % (TABLENAME, agent2, model, "', '".join(self.OBTAINABLE_GENERAL_PREDICATES)))}

                    # instill in agent1 his supposed knowledge about agent2 :
                    #--------------------------------------------------------
                    if obtainable_ground:
                    # things about agent2 that the robot assums that is known by agent1 because of
                    # the visibility of the agent2
                        for s,p,o,lh in obtainable_ground:

                            if o=='self':
                                o = model.replace('_',' ').split()[-1]
                            #if o==agent1:
                            #    o = 'self'

                            if llh > 0.5:
                                self.newstmts += [(s, p, o, new_model, lh)]
                            else:
                                self.newstmts += [(s, p, o, new_model, 0.5)] 


                # the modeler knows that agent1 and agent2 are agents :
                #------------------------------------------------------
                self.newstmts += [(agent1, 'rdf:type', 'Agent', model, llh)]
                self.newstmts += [(agent2, 'rdf:type', 'Agent', model, llh)]


    # CONTRARY/CONFLICTS methods :
    #=============================

    # TODO



    # UPDATE methods :
    #=================

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
            print 'fuck!!!'
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
        nodes = [[ s, p, o, model, "%s%s%s%s"%(s,p,o, model)] for s,p,o,model,llh in self.newstmts]
        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o,model,llh in self.newstmts]
        llh_nodes = [[ llh, "%s%s%s%s"%(s,p,o, model) ] for s,p,o,model,llh in self.newstmts]

        #with self.shareddb:
        #-------------------

        # the process are finished
        self.shareddb.execute(''' UPDATE %s SET modified=0 
                      WHERE modified=1''' % TABLENAME)

        self.shareddb.executemany('''INSERT OR IGNORE INTO %s
             (subject, predicate, object, model, id)
             VALUES (?, ?, ?, ?, ?)''' % TABLENAME, nodes) 
        #self.shareddb.executemany('''UPDATE %s SET infered=1 WHERE id=?''' % TABLENAME, ids)
        # after this, all the infered nodes (reached by reason) are set with 'infered'=1 (default value)

        # update the trust just for the infered nodes

        for llh, node in llh_nodes:
            cur = self.shareddb.execute('''SELECT trust FROM %s WHERE id=? '''% TABLENAME, [node])
            lh = cur.fetchone()[0]
            trust = llh
            if (lh-llh)*(lh-llh)==1:
                pass
            elif lh==llh: # if nothing new dont care (TODO : better comment or find other hack)
                pass      # want to still take it into account if infered = 1 => need to solve this problem !
            else:
                trust = lh*llh/( lh*llh + (1-lh)*(1-llh) )
            self.shareddb.execute(''' UPDATE %s SET trust=%f
                                WHERE id=?''' % (TABLENAME, trust), [node])
            #self.shareddb.execute(''' UPDATE %s SET trust=%f
            #                    WHERE id=? AND infered=1''' % (TABLENAME, trust), [node])

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
            LOGGER.info('reasonner starts')
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

# threading functions :
#======================

reason = None

def reasoner_start():
    global reason

    if not reason:
        reason = Reasoner()
    reason.running = True
    reason()



def reasoner_stop():
    global reason

    if reason:
        reason.running = False



# TESTING :
#==========

if __name__ == '__main__':

    reason = Reasoner()
    reason.classify()
    reason.update_models()
    reason.shareddb.close()
    reason.db.close()
