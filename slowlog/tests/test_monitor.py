
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestMonitor(unittest.TestCase):

    def setUp(self):
        self.reported = []

    def tearDown(self):
        pass

    @property
    def _class(self):
        from slowlog.monitor import Monitor
        return Monitor

    def _make(self):
        obj = self._class()
        return obj

    def _make_reporter(self, report_at=0, ident='x', report_error=None):
        reported = self.reported

        class DummyReporter:
            def __init__(self):
                self.report_at = report_at
                self.ident = ident

            def __call__(self, frame):
                reported.append(frame)
                self.report_at += 30.0
                if report_error is not None:
                    raise report_error

        return DummyReporter()

    def _make_nosleep_queue(self):
        self.queue_gets = queue_gets = []

        class DummyQueue:
            def empty(self):
                return True

            def get(self, timeout):
                queue_gets.append(timeout)
                # Return the stop signal
                return None

        return DummyQueue()

    def test_add(self):
        obj = self._make()
        reporter = self._make_reporter()
        obj.add(reporter)
        self.assertFalse(obj.queue.empty())
        self.assertFalse(obj.reporters)
        self.assertEqual(obj.queue.get(), (reporter, True))

    def test_remove(self):
        obj = self._make()
        reporter = self._make_reporter()
        obj.remove(reporter)
        self.assertFalse(obj.queue.empty())
        self.assertFalse(obj.reporters)
        self.assertEqual(obj.queue.get(), (reporter, False))

    def test_run_after_add_one(self):
        obj = self._make()
        reporter = self._make_reporter()
        obj.add(reporter)
        obj.queue.put(None)
        obj.run()
        self.assertEqual(obj.reporters, set([reporter]))

    def test_run_after_remove_one(self):
        obj = self._make()
        reporter = self._make_reporter()
        obj.reporters.add(reporter)
        obj.remove(reporter)
        obj.queue.put(None)
        obj.run()
        self.assertEqual(obj.reporters, set())

    def test_run_after_add_2_and_remove_1(self):
        obj = self._make()
        reporter1 = self._make_reporter()
        obj.add(reporter1)
        reporter2 = self._make_reporter()
        obj.add(reporter2)
        obj.remove(reporter1)
        obj.queue.put(None)
        obj.run()
        self.assertEqual(obj.reporters, set([reporter2]))

    def test_run_without_reporters(self):
        obj = self._make()
        obj.queue = self._make_nosleep_queue()
        obj.run()
        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0]
        self.assertIsNone(t)

    def test_run_with_future_reporters(self):
        now = time.time()
        obj = self._make()
        obj.queue = self._make_nosleep_queue()

        reporter1 = self._make_reporter(report_at=now + 2400.0)
        obj.reporters.add(reporter1)
        reporter2 = self._make_reporter(report_at=now + 1800.0)
        obj.reporters.add(reporter2)

        obj.run()
        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0]
        self.assertGreater(t, 0)
        self.assertLess(t, 1800.0)

    def test_run_with_an_immediate_reporter_and_a_postponed_reporter(self):
        now = time.time()
        obj = self._make()
        obj.queue = self._make_nosleep_queue()

        reporter1 = self._make_reporter(report_at=now)
        obj.reporters.add(reporter1)
        reporter2 = self._make_reporter(report_at=now + 1800.0)
        obj.reporters.add(reporter2)

        obj.run()

        self.assertEqual(len(self.reported), 1)
        frame = self.reported[0]
        self.assertIsNone(frame)

        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0]
        self.assertGreater(t, 0)
        self.assertLess(t, 1800.0)

    def test_run_with_call_frame(self):
        from Queue import Queue
        import thread

        start_queue = Queue()
        end_queue = Queue()

        def run():
            start_queue.put(thread.get_ident())
            end_queue.get()

        thread.start_new_thread(run, ())
        try:
            ident = start_queue.get()  # Wait for the thread to start.
            obj = self._make()
            obj.queue = self._make_nosleep_queue()
            now = time.time()
            reporter = self._make_reporter(report_at=now, ident=ident)
            obj.reporters.add(reporter)
            obj.run()
        finally:
            end_queue.put(None)  # Let the thread end.

        self.assertEqual(len(self.reported), 1)
        frame = self.reported[0]
        self.assertIsNotNone(frame)
        self.assertIsNotNone(frame.f_code.co_filename)
        self.assertIsNotNone(frame.f_code.co_name)

        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0]
        self.assertGreater(t, 20.0)
        self.assertLess(t, 30.0)

    def test_run_with_broken_reporter(self):
        now = time.time()
        obj = self._make()
        obj.queue = self._make_nosleep_queue()

        reporter = self._make_reporter(report_at=now,
                                       report_error=ValueError('synthetic'))
        obj.reporters.add(reporter)

        obj.run()

        self.assertEqual(len(self.reported), 1)
        frame = self.reported[0]
        self.assertIsNone(frame)

        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0]
        self.assertGreater(t, 20.0)
        self.assertLess(t, 30.0)

    def test_run_when_timeout_reached(self):
        from Queue import Empty
        queue_gets = []
        queue_contents = [Empty(), None]

        class DummyQueue:
            def empty(self):
                return True

            def get(self, timeout):
                queue_gets.append(timeout)
                item = queue_contents.pop(0)
                if item is None:
                    return None
                else:
                    raise item

        now = time.time()
        obj = self._make()
        obj.queue = DummyQueue()

        reporter = self._make_reporter(report_at=now)
        obj.reporters.add(reporter)

        obj.run()

        self.assertEqual(len(self.reported), 1)
        frame = self.reported[0]
        self.assertIsNone(frame)

        self.assertEqual(len(queue_gets), 2)

        t = queue_gets[0]
        self.assertGreater(t, 20.0)
        self.assertLess(t, 30.0)

        t = queue_gets[1]
        self.assertGreater(t, 20.0)
        self.assertLess(t, 30.0)


class Test_get_monitor(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        from slowlog.monitor import _monitor
        if _monitor is not None:
            _monitor.stop()

    def _call(self):
        from slowlog.monitor import get_monitor
        return get_monitor()

    def test_once(self):
        monitor = self._call()
        self.assertIsNotNone(monitor)
        self.assertFalse(monitor.reporters)
        self.assertTrue(monitor.queue.empty())

    def test_twice(self):
        monitor1 = self._call()
        monitor2 = self._call()
        self.assertIs(monitor1, monitor2)

    def test_auto_restart(self):
        monitor1 = self._call()
        monitor1.stop()
        monitor2 = self._call()
        self.assertIsNot(monitor1, monitor2)
