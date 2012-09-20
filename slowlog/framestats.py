
from perfmetrics import statsd_client
from thread import get_ident
import time


def report_framestats(frame, max_buf=1000):
    """Send info about a frame to the configured Statsd server"""
    client = statsd_client()
    if client is None:
        return

    f = frame
    buf = []
    bytecount = 0
    while f is not None:
        co = f.f_code
        name = '%s.%s' % (co.co_filename, co.co_name)
        # Record the frame stats in 2 forms, hierarchical and flat, to make
        # the stats easy to browse.
        # Notice how "flat" the underscore character is. ;-)
        client.incr('slowlog.%s' % name, buf=buf)
        client.incr('slowlog._.%s' % name.replace('.', '_'), buf=buf)
        bytecount += len(buf[-2]) + len(buf[-1]) + 2
        if bytecount >= max_buf:
            client.sendbuf(buf[:-2])
            del buf[:-2]
            bytecount = len(buf[0]) + len(buf[1]) + 1
        f = f.f_back

    if buf:
        client.sendbuf(buf)


class FrameStatsReporter(object):
    """Reporter that calls report_framestats"""

    def __init__(self, report_at, interval, ident=None):
        self.report_at = report_at
        self.interval = interval
        if ident is None:
            ident = get_ident()
        self.ident = ident

    def __call__(self, frame=None, report_framestats=report_framestats):
        now = time.time()
        self.report_at = now + self.interval
        if frame is not None:
            report_framestats(frame)
