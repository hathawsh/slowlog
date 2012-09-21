
from slowlog.compat import Empty
from slowlog.compat import Queue
from threading import Lock
from threading import Thread
import logging
import sys
import time

log = logging.getLogger(__name__)


class ReporterInterface(object):
    """The interface of Reporter objects.

    Create an object that provides this interface, then add it to the
    current Monitor before doing something that needs to be monitored;
    remove the reporter when done.
    """
    ident = 0       # thread.get_ident()
    report_at = 0   # a Unix time
    interval = 1.0  # Seconds between reports (after report_at)

    def __call__(self, report_time, frame=None):  # pragma no cover
        """Report the thread's current activity.

        This may include logging the stack or reporting statistics.
        The frame, if given, represents the thread state close to
        report_time.
        """


class Monitor(Thread):
    """A thread that reports info about activities longer than some threshold.
    """
    min_interval = 0.01

    def __init__(self):
        super(Monitor, self).__init__(name='slowlog_monitor')
        self.setDaemon(True)
        self.queue = Queue()  # Thread communication: [(reporter, add) or None]
        self.reporters = set()  # set([Reporter])

    def add(self, reporter):
        """Add a Reporter."""
        self.queue.put((reporter, True))

    def remove(self, reporter):
        """Remove a Reporter."""
        self.queue.put((reporter, False))

    def run(self, time=time.time):
        try:
            queue = self.queue

            while True:
                if not queue.empty():
                    block = False
                    timeout = None
                elif self.reporters:
                    report_time = time()
                    timeout_at = report_time + 3600.0
                    frames = None
                    for reporter in self.reporters:
                        if report_time >= reporter.report_at:
                            if frames is None:
                                frames = sys._current_frames()
                            frame = frames.get(reporter.ident)
                            try:
                                reporter.report_at = (report_time +
                                                      reporter.interval)
                                reporter(report_time, frame)
                            except Exception:
                                log.exception("Error in reporter %s", reporter)
                        timeout_at = min(timeout_at, reporter.report_at)
                    frames = None  # Free memory
                    block = True
                    timeout = max(self.min_interval, timeout_at - report_time)
                else:
                    # Wait for a reporter.
                    block = True
                    timeout = None

                try:
                    item = queue.get(block, timeout)
                except Empty:
                    pass
                else:
                    if item is None:
                        # Stop looping.
                        break
                    reporter, add = item
                    if add:
                        self.reporters.add(reporter)
                    else:
                        self.reporters.discard(reporter)

        finally:
            global _monitor
            if _monitor_lock is not None:
                _monitor_lock.acquire()
                try:
                    if _monitor is self:
                        _monitor = None
                finally:
                    _monitor_lock.release()
            else:
                pass  # pragma no cover

    def stop(self):
        global _monitor
        _monitor = None
        self.queue.put(None)


_monitor = None
_monitor_lock = Lock()


def get_monitor():
    """Get the global Monitor and start it if it's not already running.
    """
    global _monitor
    m = _monitor
    if m is None:
        _monitor_lock.acquire()
        try:
            if _monitor is None:
                _monitor = m = Monitor()
                m.start()
            else:
                pass  # pragma no cover
        finally:
            _monitor_lock.release()
    return m
