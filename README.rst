Introduction
============

Simple repository to work on load testing scripts for guillotina.

Eventually, we'll have this automated to check every change for obvious regressions.


Installation
------------

Simple virtual and aiohttp installed is all you need::

    virtualenv .
    ./bin/pip install aiohttp


Running
-------

Make sure you have a guillotina server on port 8080 and then::

    ./bin/python lt.py
