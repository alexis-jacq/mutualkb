import sqlite3

KBNAME = 'kb.db'
TABLENAME = 'nodes'
TABLE = ''' CREATE TABLE IF NOT EXISTS %s
                    ("subject" TEXT NOT NULL , 
                    "predicate" TEXT NOT NULL , 
                    "object" TEXT NOT NULL , 
                    "model" TEXT NOT NULL ,
		    "likelihood" FLOAT DEFAULT 0.5 NOT NULL,
		    "topic" TEXT DEFAULT "conceptual" NOT NULL,
		    "assumed" BOOLEAN DEFAULT 0 NOT NULL,
		    "active" INT DEFAULT 0 NOT NULL,
		    "time" INT DEFAULT 0 NOT NULL,
                    "id" TEXT PRIMARY KEY NOT NULL UNIQUE)'''

	
class KB:

	def __init__(self):
		self.conn = sqlite3.connect(KBNAME)
		self.create_kb()

	def create_kb(self):
		with self.conn:
			self.conn.execute(TABLE % TABLENAME)

	def save(self):
		self.conn.commit()

	def close(self):
		self.conn.close()



	# REASON/WORLD/DIALOG methods
	#-------------------------

	def add(self, stmts, model, likelihood=None, topic=None):
		''' stmts = statements = list of triplet 'subject, predicate, object'. ex: [[ s1, p1, o1], [s2, p2, o2], ...]
		this methode adds nodes to the table with statments attached to the selected model and increases likelihoods
		it returns a list of value that measur the importance of the added nodes to capt attention'''

		nodes = [[ s, p, o, model, "%s%s%s%s"%(s,p,o, model) ] for s,p,o in stmts]
		self.conn.executemany('''INSERT OR IGNORE INTO %s
                                       (subject, predicate, object, model, id )
                                       VALUES (?, ?, ?, ?, ?)''' % TABLENAME, nodes)

		ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]

		matters = []
		for node_id in ids:
			cursor=self.conn.cursor()
			cursor.execute('''SELECT likelihood FROM %s WHERE (id = ?)''' % TABLENAME, node_id)
			matters.append(1-cursor.fetchone()[0])

		if topic:
			self.conn.executemany('''UPDATE %s SET topic='%s' WHERE id=?''' % (TABLENAME, topic), ids)

                if likelihood:
                        self.conn.executemany('''UPDATE %s SET likelihood=((SELECT likelihood) +
                                              2 * (%f-0.5) * (1-(SELECT likelihood)) ) 
                                              WHERE id=?''' % (TABLENAME, likelihood), ids)
		return matters

		
	def sub(self, stmts, model, unlikelihood=None):
		''' the unlikeliihood is the likelihood for the statement to be false, for ex, the likelihood of a contrary statement '''
		'''stmts = this methode decreases likelihoods of nodes with statments attached to the selected model '''

		ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]

		if likelihood:
                	self.conn.executemany('''UPDATE %s SET likelihood=((SELECT likelihood) +
                                              2 * (0.5-%f) * (SELECT likelihood) ) 
                                              WHERE id=?''' % (TABLENAME, unlikelihood) , ids)
	

	def assum(self, stmts, model):

		ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]
		
		self.conn.executemany('''UPDATE %s SET assumed=1 WHERE id=?''' % TABLENAME, ids)
		
	def refute(self, stmts, model):

		ids = [("%s%s%s%s"%(s,p,o, model),) for s,p,o in stmts]

		self.conn.executemany('''UPDATE %s SET assumed=0 WHERE id=?''' % TABLENAME, ids)

	
	# THOUGHT methods
	#----------------------------
	
	def fire(self, ids):
		'''stmts = this methode actives the selected nodes'''
	
		self.conn.executemany('''UPDATE %s SET active=5 WHERE id=?''' % TABLENAME, ids)


	def douse(self, ids):
		'''stmts = this methode disactives the selected nodes '''

		self.conn.executemany('''UPDATE %s SET active=0 WHERE id=?''' % TABLENAME, ids)


	def kill(self, ids):
		'''this methode removes the selected nodes '''

		self.conn.executemany('''DELETE FROM %s WHERE id=?''' % TABLENAME, ids)


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

	matters = kb.add([[ 'self', 'rdf:type', 'robot'],['clouds','hide','mountains']],'K_self',0.5,'general')
	#print(matters)
	#kb.sub([['clouds','hide','mountains']],'K_self',0.3)
	matter = kb.add([['clouds','hide','mountains']],'K_self', 0.6)
	#print(matter)
	kb.add([['robot','rdfs:subClassOf','agent'],['agent','rdfs:subClassOf','humanoide'],['clouds','rdfs:subClassOf','landscape'],['human','rdfs:subClassOf','animals']],'K_self',0.5,'general')

        kb.add([['robot','owl:equivalentClass','machine'],['machine','owl:equivalentClass','automate']],'K_self',0.5,'general')

	kb.add([['animals','rdfs:subClassOf','alive'], ['human','rdfs:subClassOf','agent']],'K_self',0.5,'general')

	kb.fire([('selfrdf:typerobotK_self',),('animalsrdfs:subClassOfaliveK_self',),('humanrdfs:subClassOfagentK_self',)])

	
	#test = kb.testumpty()
	#if test:
	#	print('ok')
	#else:
	#	print('ko')
	
	#kb.kill([("%s%s%s%s"%('self','is','robot','K_self'),)])

	#kb.add([[ 'self', 'is', 'robot'],['clouds','hide','mountains']],'K_self',0.6)

	kb.save()
	kb.close()

