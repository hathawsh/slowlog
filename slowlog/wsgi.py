
from cStringIO import StringIO
from pprint import pformat
from slowlog.framestats import FrameStatsReporter
from slowlog.logfile import make_file_logger
from slowlog.monitor import get_monitor
from thread import get_ident
import logging
import time
import traceback
import urllib

default_log = logging.getLogger('slowlog.wsgi')


class FrameStatsApp(object):
    """WSGI app that logs Python frames involved in slow requests to statsd.

    Increments a counter for each frame currently involved in the request.
    Counters for slow code will increase more quickly than fast code.
    """
    def __init__(self, next_app, timeout=2.0, interval=1.0, frame_limit=100):
        self.next_app = next_app
        self.timeout = timeout
        self.interval = interval
        self.frame_limit = frame_limit
        self.get_monitor = get_monitor  # test hook

    def __call__(self, environ, start_response):
        monitor = self.get_monitor()
        report_at = time.time() + self.timeout
        reporter = FrameStatsReporter(report_at, self.interval,
                                      self.frame_limit)
        monitor.add(reporter)
        try:
            return self.next_app(environ, start_response)
        finally:
            monitor.remove(reporter)


def make_framestats(next_app, _globals, **kw):
    """Paste entry point for creating a FrameStatsApp"""
    timeout = float(kw.get('timeout', 2.0))
    interval = float(kw.get('interval', 1.0))
    return FrameStatsApp(next_app, timeout=timeout, interval=interval)


class SlowLogApp(object):
    """Log slow requests in a manner similar to Products.LongRequestLogger.
    """
    def __init__(self, next_app, timeout=2.0, interval=1.0, logfile=None,
                 frame_limit=100,
                 hide_env=('HTTP_COOKIE', 'paste.cookies', 'beaker.session')):
        self.next_app = next_app
        self.timeout = timeout
        self.interval = interval
        self.frame_limit = frame_limit
        if logfile:
            self.log = make_file_logger(logfile)
        else:
            self.log = logging.getLogger('slowlog')
        self.hide_env = hide_env
        self.get_monitor = get_monitor  # test hook

    def __call__(self, environ, start_response):
        monitor = self.get_monitor()
        now = time.time()
        report_at = now + self.timeout
        logger = SlowRequestLogger(self, environ, now, report_at)
        monitor.add(logger)
        try:
            return self.next_app(environ, start_response)
        finally:
            monitor.remove(logger)


def make_slowlog(next_app, _globals, **kw):
    """Paste entry point for creating a SlowLogApp"""
    timeout = float(kw.get('timeout', 2.0))
    interval = float(kw.get('interval', 1.0))
    hide_env = kw.get('hide_env',
                      'HTTP_COOKIE paste.cookies beaker.session').split()
    logfile = kw.get('file')
    return SlowLogApp(next_app, timeout=timeout, interval=interval,
                      hide_env=hide_env, logfile=logfile)


class SlowRequestLogger(object):
    """Logger for a particular request"""
    logged_first = False

    def __init__(self, app, environ, start, report_at, ident=None):
        self.app = app
        self.environ = environ
        self.start = start
        self.report_at = report_at
        if ident is None:
            ident = get_ident()
        self.ident = ident
        self.interval = app.interval

    def __call__(self, report_time, frame=None):
        elapsed = report_time - self.start
        env = self.environ
        url = construct_url(env)
        lines = ['request: %s %s' % (env.get('REQUEST_METHOD'), url)]
        if not self.logged_first:
            env = env.copy()
            for key in self.app.hide_env:
                if key in env:
                    env[key] = Hidden()
            lines.append('environ: %s' % pformat(env))
            self.logged_first = True

        if frame is not None:
            limit = self.app.frame_limit
            if limit > 0:
                tb = StringIO()
                tb.write('Traceback:\n')
                traceback.print_stack(frame, limit=limit, file=tb)
                lines.append(tb.getvalue())
            del frame

        log = self.app.log
        log.warning("Thread %s: Started on %.1f; "
                    "Running for %.1f secs; %s",
                    self.ident, self.start, elapsed, '\n'.join(lines))


class Hidden(object):
    def __repr__(self):
        return '<hidden>'


# construct_url is mostly copied from Paste (paste.request).
# This version will be made to work on Python 3.
def construct_url(environ):
    """Reconstructs the URL from the WSGI environment.
    """
    scheme = environ['wsgi.url_scheme']
    parts = [scheme, '://']
    append = parts.append

    host = environ.get('HTTP_HOST')
    if host:
        port = None
        if ':' in host:
            host, port = host.split(':', 1)
            if scheme == 'https':
                if port == '443':
                    port = None
            elif scheme == 'http':
                if port == '80':
                    port = None
        append(host)
        if port:
            append(':%s' % port)
    else:
        append(environ['SERVER_NAME'])
        port = str(environ['SERVER_PORT'])
        if scheme == 'https':
            if port != '443':
                append(':%s' % port)
        else:
            if port != '80':
                append(':%s' % port)

    append(urllib.quote(environ.get('SCRIPT_NAME','')))
    append(urllib.quote(environ.get('PATH_INFO','')))
    if environ.get('QUERY_STRING'):
        append('?%s' % environ['QUERY_STRING'])
    return ''.join(parts)
