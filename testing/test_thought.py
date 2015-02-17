#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import unittest
import time
from mutualkb import __version__, kb, processkb, ansistrm

DEFAULT_MODEL = processkb.DEFAULT_MODEL
REASONING_DELAY = 3

def version():
    print("minimalKB's thought tests %s" % __version__)

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='Test for thought.py.')

    parser.add_argument('-v', '--version', action='version',
            version=version(), help='returns mutualKB version')

    args = parser.parse_args()


    # console messages :

    console = ansistrm.ColorizingStreamHandler()
    kblogger = logging.getLogger('mylog')

    kblogger.setLevel(logging.INFO)

    #formatter = logging.Formatter('%(asctime)-15s: %(message)s')
    #console.setFormatter(formatter)
    kblogger.addHandler(console)



    kb = kb.KB()
    kb.clear()
    pkb = processkb.processKB(kb)

    pkb.start_services()

    pkb.add([['2','2','1']],0.7)

    time.sleep(1)

    pkb.add([['2', '2', '2']],0.4)

    time.sleep(1)

    pkb.add([['3', '3', '3']],0.4)



    pkb.add([['2', '2', '4']],0.4)



    pkb.add([['2', '2', '5']],0.4)

    time.sleep(10)

    pkb.add([['2', '2', '6']],0.4)

    time.sleep(5)

    pkb.add([['2', '2', '3']],0.4)



    pkb.add([['2', '2', '8']],0.4)

    time.sleep(3)

    pkb.add([['2', '2', '9']],0.4)

    time.sleep(1)

    pkb.add([['2', '1', '1']],0.4)

    time.sleep(20)

    pkb.stop_services()


