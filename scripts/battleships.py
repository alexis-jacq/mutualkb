#! /usr/bin/python
# encoding: utf-8

from gi.repository import Gtk
from mutualkb import __version__, kb, processkb
import time
import random

DEFAULT_MODEL = processkb.DEFAULT_MODEL
MYSELF = list(DEFAULT_MODEL)[0]
MYTURNE = False

class AI:
    THRESHOLD = 0.7 # trust value for whish I decide to shot
    TRUST_LEVEL = 0.5 # level of trust facing a new model : 1 => naive, 0 => septic
    LETTERS = ['a']
    NUMBERS = ['1','2','3']

    def __init__(self):
        self.kb = kb.KB()
        self.kb.clear()
        self.pkb = processkb.processKB(self.kb)
        self.model_trust = [(MYSELF,1.)]
        self.end = False

    def get_active_trials(self):
        inThought = self.kb.get_thought()
        active_trials = []
        for s,p,o,t,m,l in inThought:
            if p=='on':
                letter=o[0]
                number=o[1]
                active_trials.append((t,s,p,letter,number,m,l))
        return sorted(active_trials)


    def action(self):
        global MYTURNE

        active_trials = self.get_active_trials()
        if active_trials:
            t,s,p,letter,number,m,l = active_trials[0]

            if m.split('_')[-1]=='myself': # concerning my grid
                if l>self.THRESHOLD:
                    print 'you know that I have a ship on %s'% letter+number # + ', fuck you..'
                elif l>0.5:
                    print 'you think that I have a ship on %s'% letter+number
            if m.split('_')[-1]=='you': # concerning the grid of the ennemy
                if MYTURNE:
                    print 'shot your ship on %s'% letter+number
                    MYTURNE=False
                else:
                    if l>self.THRESHOLD:
                        print 'I know you have a ship on %s'% letter+number
                    elif l>0.5:
                        print 'I think you have a ship on %s'% letter+number

    def strategy(self):
        ''' first of all, completly random '''

        trust = random.random()
        cell = random.choice(['a1','b1','c1'])
        model = random.choice([MYSELF,'M_myself:K_you','M_myself:M_you:K_myself'])

        self.pkb.models = {model}
        self.pkb.add([['ship', 'on', cell]],trust)


    def start(self):
        self.pkb.start_services()

        while not self.end:
            self.strategy()
            self.action()
            time.sleep(5)

    def stop(self):
        self.end = True
        self.pkb.stop_services()
'''
class GUI:

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('battleships.glade')
        self.builder.connect_signals(self)
        self.textbuffer = self.builder.get_object("textview1").get_buffer()
        self.window = self.builder.get_object("window1")
        if (self.window):
            self.window.connect("destroy", self.onDestroy)
        self.window.show_all()
        self.ai = AI()
        AI.start()

    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)

    def text1(self, button):
        print 'test ok'

    def onSend(self, button):
        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        text = self.textbuffer.get_text(start_iter, end_iter, True) 
        print(text)

    def onWrite(self, button):
        text = self.builder.get_object("entry1").get_text()
        print(text)

    def onDestroy(self):
        AI.stop()
        Gtk.main_quit()
'''

if __name__ == "__main__":
    #GUI()
    #Gtk.main()

    ai = AI()
    ai.start()

