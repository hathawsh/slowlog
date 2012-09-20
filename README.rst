
Introduction
============

The slowlog library helps you find out why certain code paths are slow.
It works in a WSGI environment, as a Pyramid tween, or as a simple
context manager or decorator.  It is inspired by Products.LongRequestLogger.

The library can log stack frames like Products.LongRequestLogger does,
but it can also log frame statistics to Graphite using Statsd, making it
possible to create real-time graphs that reveal which code is spending
more time than expected.

The library works by creating a monitor thread.  Other threads add
call loggers to the monitor thread and the monitor thread calls
those loggers periodically if the call lasts longer than a timeout.
The sys._current_frames() function is used to gather stack traces, so
not all Python implementations are supported.

Usage
=====

In progress.

Reference Documentation
=======================

In progress.
