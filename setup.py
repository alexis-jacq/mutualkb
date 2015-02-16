#!/usr/bin/env python
 # -*- coding: utf-8 -*-

import os
from distutils.core import setup

execfile('src/mutualkb/__init__.py')

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='mutualkb',
      version='0.1',
      license='BSD3',
      description='A SQLite-based knowledge data base designed to perform both onthological reasoning and mutual modeling.',
      long_description=readme(),
      classifiers=[
        'License :: OSI Approved :: BSD-3 License',
        'Programming Language :: Python :: 2.7',
      ],
      author='Alexis David Jacq',
      author_email='alexis.jacq@gmail.com',
      url='https://github.com/severin-lemaignan/minimalkb',
      requires=['pysqlite', 'rdflib'],
      package_dir = {'': 'src'},
      packages=['mutualkb'],
      data_files=[('share/doc/mutualkb', ['LICENSE', 'README.md'])]
      )
