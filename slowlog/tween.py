
from cStringIO import StringIO
from pprint import pformat
from slowlog.framestats import FrameStatsLogger
from slowlog.monitor import get_monitor
from thread import get_ident
import logging
import time
import traceback

default_log = logging.getLogger('slowlog.tween')


class FrameStatsTween(object):
    """Log the Python frames involved in slow requests to statsd.
    """
    def __init__(self, handler, registry):
        self.handler = handler
        settings = registry.settings
        self.timeout = float(settings.get('framestats_timeout', 2.0))
        self.interval = float(settings.get('framestats_interval', 0.1))

    def __call__(self, request, monitor=None):
        if monitor is None:
            monitor = get_monitor()
        log_at = time.time() + self.timeout
        logger = FrameStatsLogger(log_at, self.interval)
        monitor.add(logger)
        try:
            return self.handler(request)
        finally:
            monitor.remove(logger)


class SlowLogTween(object):
    """Log slow requests in a manner similar to Products.LongRequestLogger.
    """
    def __init__(self, handler, registry, log=default_log):
        self.handler = handler
        settings = registry.settings
        self.timeout = float(settings.get('slowlog_timeout', 2.0))
        self.interval = float(settings.get('slowlog_interval', 1.0))
        self.log = log
        default_hide = 'password'
        self.hide_post_vars = settings.get('slowlog_hide_post_vars',
                                           default_hide).split()

    def __call__(self, request, monitor=None):
        if monitor is None:
            monitor = get_monitor()
        now = time.time()
        log_at = now + self.timeout
        logger = TweenRequestLogger(self, request, now, log_at)
        monitor.add(logger)
        try:
            return self.handler(request)
        finally:
            monitor.remove(logger)


class TweenRequestLogger(object):
    logged_first = False

    def __init__(self, tween, request, start, log_at, ident=None):
        self.tween = tween
        self.request = request
        self.start = start
        self.log_at = log_at
        if ident is None:
            ident = get_ident()
        self.ident = ident

    def log(self, frame=None):
        now = time.time()
        self.log_at = now + self.tween.log_interval
        elapsed = now - self.start
        request = self.request
        lines = ['request: %s %s' % (request.request_method, request.url)]

        if not self.logged_first:
            if request.POST:
                post = {}
                post.update(request.POST)
                for key in self.tween.hide_env:
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
        log.warning("Thread %s: Started on %.1f; "
                    "Running for %.1f secs; %s",
                    self.ident, self.start, elapsed, '\n'.join(lines))


class Hidden(object):
    def __repr__(self):
        return '<hidden>'
