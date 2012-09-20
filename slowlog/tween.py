
from cStringIO import StringIO
from pprint import pformat
from slowlog.framestats import FrameStatsReporter
from slowlog.logfile import make_file_logger
from slowlog.monitor import get_monitor
from thread import get_ident
import logging
import time
import traceback


class FrameStatsTween(object):
    """Log the Python frames involved in slow requests to statsd.

    Increments a counter for each frame currently involved in the request.
    Counters for slow code will increase more quickly than fast code.
    """
    def __init__(self, handler, registry):
        self.handler = handler
        settings = registry.settings
        self.timeout = float(settings.get('framestats_timeout', 2.0))
        self.interval = float(settings.get('framestats_interval', 0.1))
        self.get_monitor = get_monitor  # testing hook

    def __call__(self, request):
        monitor = self.get_monitor()
        report_at = time.time() + self.timeout
        reporter = FrameStatsReporter(report_at, self.interval)
        monitor.add(reporter)
        try:
            return self.handler(request)
        finally:
            monitor.remove(reporter)


class SlowLogTween(object):
    """Log slow requests in a manner similar to Products.LongRequestLogger.
    """
    def __init__(self, handler, registry):
        self.handler = handler
        settings = registry.settings
        self.timeout = float(settings.get('slowlog_timeout', 2.0))
        self.interval = float(settings.get('slowlog_interval', 1.0))
        logfile = settings.get('slowlog_file')
        if logfile:
            self.log = make_file_logger(logfile)
        else:
            self.log = logging.getLogger('slowlog')
        default_hide = 'password'
        self.hide_post_vars = settings.get('slowlog_hide_post_vars',
                                           default_hide).split()
        self.get_monitor = get_monitor  # testing hook

    def __call__(self, request):
        monitor = self.get_monitor()
        now = time.time()
        report_at = now + self.timeout
        logger = TweenRequestLogger(self, request, now, report_at)
        monitor.add(logger)
        try:
            return self.handler(request)
        finally:
            monitor.remove(logger)


class TweenRequestLogger(object):
    """Logger for a particular request"""
    logged_first = False

    def __init__(self, tween, request, start, report_at, ident=None):
        self.tween = tween
        self.request = request
        self.start = start
        self.report_at = report_at
        if ident is None:
            ident = get_ident()
        self.ident = ident

    def __call__(self, frame=None):
        now = time.time()
        self.report_at = now + self.tween.interval
        elapsed = now - self.start
        request = self.request
        lines = ['request: %s %s' % (request.method, request.url)]

        if not self.logged_first:
            if request.POST:
                post = {}
                post.update(request.POST)
                for key in self.tween.hide_post_vars:
                    if key in post:
                        post[key] = Hidden()
                lines.append('post: %s' % pformat(post))
            self.logged_first = True

        if frame is not None:
            tb = StringIO()
            tb.write('Stack:\n')
            traceback.print_stack(frame, file=tb)
            del frame
            lines.append(tb.getvalue())

        log = self.tween.log
        msg = '\n'.join(lines)
        log.warning("Thread %s: Started on %.1f; "
                    "Running for %.1f secs; %s",
                    self.ident, self.start, elapsed, msg)


class Hidden(object):
    def __repr__(self):
        return '<hidden>'
