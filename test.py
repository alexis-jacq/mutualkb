#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import unittest
import time
import kb
import processkb
from minimalkb import __version__
from Queue import Empty

DEFAULT_MODEL = processkb.DEFAULT_MODEL
REASONING_DELAY = 3

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.kb = kb.KB()
        self.pkb = processkb.processKB(self.kb)

    # KB TEST
    #========

    def test_basic_modifications(self):
        # check no exception is raised
        #-----------------------------

        # test basic add and sub
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.6)
        self.pkb.sub([[ 'mouse', 'sees', 'snake']], 0.6)

        # test sub for non-existing node
        self.pkb.sub([['duck', 'seeks', 'snail']], 0.7)

        # test adding of common/shared ground
        self.pkb.add_common([['dogs', 'are', 'happy']], 0.7)
        self.pkb.add_shared([['cats', 'are', 'sorry']], 0.7)

        # test default agruments
        self.pkb.add([[ 'fox', 'sees', 'owl']])
        self.pkb.sub([[ 'fox', 'sees', 'owl']])
        self.pkb.add_common([['dogs', 'are', 'deep']])
        self.pkb.add_shared([['cats', 'are', 'universal']])

    def test_basic_trust_calculation(self):
        # check trust value in fuzzy-knowledge while add/sub nodes
        #---------------------------------------------------

        self.kb.clear()
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.6)
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.6)
        trust = self.kb.get_trust('mouseseessnakeK_myself')
        self.assertTrue(trust-0.692308 < 0.00001)
        self.assertTrue(trust-0.692308 > -0.00001)
        '''
        self.kb.clear()
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.5)
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.6)
        trust = self.kb.get_trust('mouseseessnakeK_myself')
        self.assertTrue(trust-0.6 < 0.00001)

        self.kb.clear()
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.0)
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.6)
        trust = self.kb.get_trust('mouseseessnakeK_myself')
        self.assertTrue(trust-0.0 < 0.00001)

        self.kb.clear()
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 1.0)
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.6)
        trust = self.kb.get_trust('mouseseessnakeK_myself')
        self.assertTrue(trust-1.0 < 0.00001)

        self.kb.clear()
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.6)
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.4)
        trust = self.kb.get_trust('mouseseessnakeK_myself')
        self.assertTrue(trust-0.5 < 0.00001)

        self.kb.clear()
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.0)
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 1.0)
        trust = self.kb.get_trust('mouseseessnakeK_myself')
        self.assertTrue(trust-1.0 < 0.00001)

        self.kb.clear()
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 1.0)
        self.pkb.add([[ 'mouse', 'sees', 'snake']], 0.0)
        trust = self.kb.get_trust('mouseseessnakeK_myself')
        self.assertTrue(trust-0.0 < 0.00001)
        '''

    def test_containing(self):

        self.kb.clear()

        self.pkb.add([[ 'mouse', 'sees', 'snake']])
        self.assertTrue([[ 'mouse', 'sees', 'snake']] in self.pkb)
        self.assertFalse([[ 'fox', 'sees', 'snake']] in self.pkb)


    # REASONER TEST
    #==============

    def test_ontologic_upstairs(self):

        self.kb.clear()
        self.pkb.add([['snake', 'rdf:type', 'Reptile']],0.7)
        self.pkb.add([['Reptile', 'rdfs:subClassOf', 'Animal']],1.0)
        self.pkb.add([['Animal', 'rdfs:subClassOf', 'Alive']],0.4)

        self.pkb.start_services()
        time.sleep(REASONING_DELAY)
        self.pkb.stop_services()

        # check existances
        self.assertTrue([['snake', 'rdf:type', 'Animal'],['snake', 'rdf:type', 'Alive']] in self.pkb)
        self.assertTrue([['Reptile', 'rdfs:subClassOf', 'Alive']] in self.pkb)
        self.assertFalse([['Reptile', 'rdf:type', 'Alive']] in self.pkb)
        self.assertFalse([['Alive', 'rdfs:subClassOf', 'Reptile']] in self.pkb)
        self.assertFalse([['Alive', 'rdfs:subClassOf', 'Animal']] in self.pkb)

        # check trust-value propagations
        t1 = self.kb.get_trust('snakerdf:typeAnimalK_myself')
        t2 = self.kb.get_trust('snakerdf:typeAliveK_myself')
        t3 = self.kb.get_trust('Reptilerdfs:subClassOfAliveK_myself')
        self.assertTrue(t1==0.7)
        self.assertTrue(t2==0.5)
        self.assertTrue(t3==0.5)

    def test_ontologic_equivalents(self):

        self.kb.clear()
        self.pkb.add([['myself', 'rdf:type', 'Robot']],0.7)
        self.pkb.add([['Robot', 'owl:equivalentClass', 'Machine']],1.0)
        self.pkb.add([['Machine', 'owl:equivalentClass', 'Automaton']],0.4)
        self.pkb.add([['Nao','rdfs:subClassOf', 'Automaton']],0.8)

        self.pkb.start_services()
        time.sleep(REASONING_DELAY)
        self.pkb.stop_services()

        # check existances
        self.assertTrue([['Robot', 'owl:equivalentClass', 'Automaton']] in self.pkb)
        self.assertTrue([['Nao', 'rdfs:subClassOf', 'Robot']] in self.pkb)
        self.assertTrue([['myself','rdf:type', 'Automaton']] in self.pkb)
        self.assertFalse([['myself', 'rdf:type', 'Nao']] in self.pkb)
        self.assertFalse([['Nao', 'owl:equivalentClass', 'Robot']] in self.pkb)

        # check trust-value propagations
        t1 = self.kb.get_trust('Robotowl:equivalentClassAutomatonK_myself')
        t2 = self.kb.get_trust('Naordfs:subClassOfRobotK_myself')
        t3 = self.kb.get_trust('myselfrdf:typeAutomatonK_myself')
        self.assertTrue(t1==0.5)
        self.assertTrue(t2==0.5)
        self.assertTrue(t3==0.5)


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='Test suite for mutualKB.')

#    parser.add_argument('-v', '--version', action='version',
#            version=version(), help='returns mutualKB version')

    parser.add_argument('-f', '--failfast', action='store_true',
            help='stops at first failed test')

    args = parser.parse_args()

    kblogger = logging.getLogger('mylog')
    console = logging.StreamHandler()

    kblogger.setLevel(logging.DEBUG)
    kblogger.addHandler(console)

    unittest.main(failfast=args.failfast)


