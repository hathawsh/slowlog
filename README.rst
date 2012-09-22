
Overview
========

The ``slowlog`` library helps you find out why some requests to your
web application take a long time.  It periodically dumps stack traces
of long running requests to a log file.  It works as a Pyramid tween
or as a WSGI component. It is inspired by ``Products.LongRequestLogger``,
which provides similar functionality for Zope 2.

This library can also log frame statistics to Graphite using the
``perfmetrics`` library, making it possible to create real-time graphs
that reveal expensive code paths.

This library uses ``sys._current_frames()`` to gather stack traces, so
it supports CPython versions 2.6+ and 3.2+, but other Python
implementations might not work.

|TravisBadge|_

.. |TravisBadge| image:: https://secure.travis-ci.org/hathawsh/slowlog.png?branch=master
.. _TravisBadge: http://travis-ci.org/hathawsh/slowlog

Installation
============

Install using setuptools, e.g. (within a virtualenv)::

    $ bin/easy_install slowlog

Pyramid Configuration
---------------------

Once the ``slowlog`` library is installed, use the ``config.include``
mechanism to add ``slowlog`` to your project.  In your Pyramid
project's ``__init__.py``::

    config = Configurator(...)
    config.include('slowlog')

Alternately, you can add the following line to your application's
``.ini`` file::

    pyramid.includes = slowlog

Next, Pyramid needs some settings before the ``slowlog`` library has
any effect.  Two tweens are available, ``slowlog`` and ``framestats``.

The slowlog tween
~~~~~~~~~~~~~~~~~

The ``slowlog`` tween periodically logs stack traces of long running
requests.  To activate it, set ``slowlog = true`` in your Pyramid settings.
The ``slowlog`` tween supports the following settings.

slowlog
    Set to ``true`` to activate the ``slowlog`` tween.  Default: false.

slowlog_timeout
    Only log stack traces of requests that last at least
    this number of seconds (floating point).  Default: 2.0.

slowlog_interval
    Once a request lasts longer than ``slowlog_timeout``, the
    ``slowlog`` tween continues to log stack traces periodically with
    the given interval in seconds (floating point). Default: 1.0.

slowlog_file
    Log all stack traces to the given file.  The file will be rotated
    automatically when it grows to 10 megabytes.  If this setting is empty or
    missing, stack traces will be logged using Python's standard
    ``logging`` module with the logger name ``slowlog``.  Default: none.

slowlog_frames
    Limit the number of frames in stack traces.  If set to 0, no stack
    traces will be logged.  Default: 100.

slowlog_hide_post_vars
    A whitespace-delimited list of POST variables that should be
    redacted (hidden) in logs.  Useful for avoiding accidental storage
    of cleartext passwords.  Default:  ``password``.

The framestats tween
~~~~~~~~~~~~~~~~~~~~

The ``framestats`` tween periodically increments Statsd counters for
all frames on the stack of long-running requests.
To activate it, set ``framestats = true`` in your Pyramid settings.
The ``framestats`` tween supports the following settings.

framestats
    Set to ``true`` to activate the ``framestats`` tween.  Default: false.

statsd_uri
    Required.  A common URI is ``statsd://localhost:8125``.  See the
    ``perfmetrics`` library for supported parameters.

framestats_timeout
    Only update Statsd for requests that last at least
    this number of seconds (floating point).  Default: 2.0.

framestats_interval
    Once a request lasts longer than ``framestats_timeout``, the
    ``framestats`` tween continues to update Statsd periodically with
    the given interval in seconds (floating point). Default: 1.0.

framestats_frames
    Limit the number of frames to follow in stack traces.
    If set to 1, Statsd will receive information about only the current
    frame.  Default: 100.
