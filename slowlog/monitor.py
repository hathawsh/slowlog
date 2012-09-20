
from Queue import Empty
from Queue import Queue
from thread import allocate_lock
from threading import Thread
import logging
import sys
import time

log = logging.getLogger(__name__)


class ThreadLogger(object):
    """ThreadLogger interface."""
    ident = 0     # thread.get_ident()
    log_at = 0    # a Unix time

    def log(self, frame=None):
        """Log the thread's current activity."""


class Monitor(Thread):
    """A thread that logs activities longer than some threshold."""
    min_interval = 0.01

    def __init__(self, *args, **kw):
        super(Monitor, self).__init__(*args, **kw)
        self.setDaemon(True)
        self.queue = Queue()
        self.loggers = set()  # set([ThreadLogger])

    def add(self, logger):
        """Add a ThreadLogger."""
        self.queue.put((logger, True))

    def remove(self, logger):
        """Remove a ThreadLogger."""
        self.queue.put((logger, False))

    def run(self):
        queue = self.queue
        while True:
            timeout = None
            if queue.empty() and self.loggers:
                now = time.time()
                timeout_at = now + 3600.0
                frames = None
                for logger in self.loggers:
                    if now >= logger.log_at:
                        if frames is None:
                            frames = sys._current_frames()
                        frame = frames.get(logger.ident)
                        try:
                            logger.log(frame)
                        except Exception:
                            log.exception("Error in logger %s", logger)
                    timeout_at = min(timeout_at, logger.log_at)
                frames = None  # Free memory
                timeout = max(self.min_interval, timeout_at - now)

            try:
                logger, add = queue.get(timeout)
            except Empty:
                pass
            else:
                if add:
                    self.loggers.add(logger)
                else:
                    self.loggers.discard(logger)


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
