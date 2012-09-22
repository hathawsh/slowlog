
from slowlog.compat import get_ident


def report_framestats(client, frame, limit=100, max_buf=1000):
    """Send info about a frame to a Statsd server"""
    f = frame
    buf = []
    bytecount = 0
    count = 0
    names = []
    while f is not None and count < limit:
        modname = f.f_globals.get('__name__', '(module)')
        co = f.f_code
        names.append('%s.%s' % (modname, co.co_name))
        if f.f_locals.get('__slowlog_barrier__'):
            # Ignore the stack beyond this point.
            break
        f = f.f_back
        count += 1

    framecount = float(len(names))
    for i, name in enumerate(names):
        # The current frame is first in the list and increments a counter by 1.
        # The rest of the frames increment counters by smaller
        # amounts.
        weight = '%0.3g' % ((framecount - i) / framecount)
        # Record the frame names in 2 forms, hierarchical and flat,
        # to make the stats easy to browse.
        client.incr('framestats.%s' % name, weight, buf=buf)
        flat_name = name.replace('.', '_')
        client.incr('framestats._.%s' % flat_name, weight, buf=buf)
        size = len(buf[-2]) + len(buf[-1]) + 2
        bytecount += size
        if bytecount >= max_buf:
            client.sendbuf(buf[:-2])
            del buf[:-2]
            bytecount = size

    if buf:
        client.sendbuf(buf)


class FrameStatsReporter(object):
    """Reporter that calls report_framestats"""

    def __init__(self, client, report_at, interval, frame_limit=100,
                 ident=None):
        self.client = client
        self.report_at = report_at
        self.interval = interval
        if ident is None:
            ident = get_ident()
        self.ident = ident
        self.frame_limit = frame_limit

    def __call__(self, _report_time, frame=None,
                 report_framestats=report_framestats):
        if frame is not None:
            report_framestats(self.client, frame, self.frame_limit)
