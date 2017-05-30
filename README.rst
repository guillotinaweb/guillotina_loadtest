Introduction
============

.. image:: https://travis-ci.org/guillotinaweb/guillotina_loadtest.svg?branch=master
   :target: https://travis-ci.org/guillotinaweb/guillotina_loadtest

Simple repository to work on load testing scripts for guillotina.

Eventually, we'll have this automated to check every change for obvious regressions.


Installation
------------

Simple virtual and aiohttp installed is all you need::

    virtualenv .
    ./bin/python setup.py develop


Running
-------

Then, just run::

    ./bin/glt


Run without creating site inline::

  ./bin/glt --skip-site-creation
