import sqlite3
import pickle

class conflicts():

	def __init__(self, kb):

		self.kb = kb()

		try:
			self.conflist = pickle.load( open( "conflist.p", "rb" ) )
		except:
			self.conflist = {}


	def update(self, stmts, model):

		for stmt in stmts:
			#...       use kb.searchConflicts

	def solve(self, stmts, model):

		for stmt in stmts:
			#...       use kb.MOST_PROBABLE_EXPLANATION (that use kb.assum and kb.refute) 


	def save(self):

		pickle.dump( self.conflist, open( "conflist.p", "wb" ) )
