import logging
logger = logging.getLogger('mylog')
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import numpy

KBNAME = 'kb.db'
TABLENAME = 'nodes'
TABLE = ''' CREATE TABLE IF NOT EXISTS %s
            ("subject" TEXT NOT NULL ,
            "predicate" TEXT NOT NULL ,
            "object" TEXT NOT NULL ,
            "model" TEXT NOT NULL ,
            "agent" TEXT NOT NULL DEFAULT "myself",
            "likelihood" FLOAT DEFAULT 0.5 NOT NULL,
            "assumed" BOOLEAN DEFAULT 0 NOT NULL,
            "active" INT DEFAULT 0 NOT NULL,
            "matter" FLOAT DEFAULT 0.5 NOT NULL,
            "infered" BOOLEAN DEFAULT 1 NOT NULL,
            "modified" BOOLEAN DEFAULT 1 NOT NULL,
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

    def add(self, stmts, model, likelihood=None):
        ''' stmts = statements = list of triplet 'subject, predicate, object'. ex: [[ s1, p1, o1], [s2, p2, o2], ...]
        this methode adds nodes to the table with statments attached to the selected model and increases likelihoods
        it returns a list of value that measur the importance of the added nodes to capt attention'''

        if likelihood or likelihood==0:
            llh = likelihood
        else:
            llh = 0.5

        self.wait_turn()

        new_stmts = []
        for s,p,o in stmts:
            if o=='?':
                stmts_to_add = {(s, p, row[0]) for row in self.conn.execute(
                            '''SELECT object FROM %s WHERE
                            model="%s" AND subject="%s" AND predicate="%s" ''' % (TABLENAME, model,s,p))}
                if stmts_to_add:
                    for stmt in stmts_to_add:
                        new_stmts.append(stmt)
                else:
                    new_stmts.append([s,p,'??'])
            else:
                new_stmts.append([s,p,o])

        stmts = new_stmts


        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
        node_ids = [("%s%s%s%s"%(s,p,o, model)) for s,p,o in stmts]


        for node_id in ids:
            cursor=self.conn.cursor()
            try:
                cursor.execute('''SELECT likelihood FROM %s WHERE (id = ?)''' % TABLENAME, node_id)
                hold_llh = cursor.fetchone()[0]
            except TypeError:
                hold_llh = 0
            matter = numpy.absolute(llh-hold_llh)
            self.conn.executemany('''UPDATE %s SET matter='%f' WHERE id=?''' % (TABLENAME, matter), ids)

        nodes = [[ s, p, o, model, 0, "%s%s%s%s"%(s,p,o, model) ] for s,p,o in stmts]
        self.conn.executemany('''INSERT OR IGNORE INTO %s
                       (subject, predicate, object, model, infered, id )
                       VALUES (?, ?, ?, ?, ?, ?)''' % TABLENAME, nodes)

        self.conn.executemany('''UPDATE %s SET modified = 1
                            WHERE id=?''' % TABLENAME, ids)

        if likelihood or likelihood==0:

            llh = likelihood
            for node in node_ids:
                cur = self.conn.execute('''SELECT likelihood FROM %s WHERE id=?'''% TABLENAME, [node])
                lh = cur.fetchone()[0]
                likelihood = llh
                if(lh-llh)*(lh-llh) == 1:
                    pass
                else:
                    likelihood = lh*llh/( lh*llh + (1-lh)*(1-llh) )

                self.conn.execute(''' UPDATE %s SET likelihood=%f 
                                    WHERE id=?''' % (TABLENAME, likelihood), [node])

        agent = model.replace('_',' ').split()[-1]
        self.conn.executemany('''UPDATE %s SET agent="%s" WHERE id=?''' % (TABLENAME, agent), ids)

        self.save()


    def sub(self, stmts, model, unlikelihood=None):
        ''' the unlikeliihood is the likelihood for the statement to be false, for ex, the likelihood of a contrary statement '''
        '''stmts = this methode decreases likelihoods of nodes with statments attached to the selected model '''

        self.wait_turn

        ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]

        if unlikelihood:
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
        try:
            test = {row[0] for row in self.conn.execute('''SELECT subject FROM %s
                WHERE (predicate='ise')
                ''' % TABLENAME )}
        except sqlite3.OperationalError:
            test = {}
        return test



