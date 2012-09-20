
from Queue import Empty
from Queue import Queue
from thread import allocate_lock
from threading import Thread
import logging
import sys
import time

log = logging.getLogger(__name__)


class Reporter(object):
    """Reporter interface.

    Create an object that provides this interface, then add it to the
    current Monitor before doing something; remove it when done.
    """
    ident = 0      # thread.get_ident()
    report_at = 0  # a Unix time

    def __call__(self, frame=None):
        """Report the thread's current activity.

        This may include logging the stack or reporting statistics.
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

    def run(self):
        try:
            queue = self.queue

            while True:
                if not queue.empty():
                    timeout = 0
                elif self.reporters:
                    now = time.time()
                    timeout_at = now + 3600.0
                    frames = None
                    for reporter in self.reporters:
                        if now >= reporter.report_at:
                            if frames is None:
                                frames = sys._current_frames()
                            frame = frames.get(reporter.ident)
                            try:
                                reporter(frame)
                            except Exception:
                                log.exception("Error in reporter %s", reporter)
                        timeout_at = min(timeout_at, reporter.report_at)
                    frames = None  # Free memory
                    timeout = max(self.min_interval, timeout_at - now)
                else:
                    # Wait for a reporter.
                    timeout = None

                try:
                    item = queue.get(timeout)
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

    def stop(self):
        global _monitor
        _monitor = None
        self.queue.put(None)


_monitor = None
_monitor_lock = allocate_lock()


def get_monitor():
    """Get the global Monitor and start it if it's not already running.
    """
    global _monitor
    if _monitor is None:
        _monitor_lock.acquire()
        try:
            if _monitor is None:
                _monitor = Monitor()
                _monitor.start()
        finally:
            _monitor_lock.release()
    return _monitor
