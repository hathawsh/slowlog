
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
                self.interval = 10.0
                self.ident = ident

            def __call__(self, report_time, frame):
                reported.append((report_time, frame))
                if report_error is not None:
                    raise report_error

        return DummyReporter()

    def _make_nosleep_queue(self):
        self.queue_gets = queue_gets = []

        class DummyQueue:
            def empty(self):
                return True

            def get(self, block=True, timeout=None):
                queue_gets.append((block, timeout))
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
        self.assertEqual(t, (True, None))

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
        t = self.queue_gets[0][1]
        self.assertGreater(t, 0)
        self.assertLess(t, 1800.0)

    def test_run_with_ready_reporters(self):
        obj = self._make()
        obj.queue = self._make_nosleep_queue()

        reporter1 = self._make_reporter(report_at=1233.9)
        obj.reporters.add(reporter1)
        reporter2 = self._make_reporter(report_at=1233.8)
        obj.reporters.add(reporter2)

        obj.run(time=lambda: 1234.0)

        self.assertEqual(len(self.reported), 2)
        self.assertEqual(self.reported, [(1234.0, None), (1234.0, None)])

        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0][1]
        self.assertGreater(t, 0)
        self.assertLess(t, 1800.0)

    def test_run_with_real_frame(self):
        # Start a thread and sample a frame from it.
        from slowlog.compat import Queue
        from slowlog.compat import get_ident
        import threading

        start_queue = Queue()
        end_queue = Queue()

        def run():
            start_queue.put(get_ident())
            end_queue.get()

        th = threading.Thread(target=run)
        th.start()
        try:
            ident = start_queue.get()  # Wait for the thread to start.
            obj = self._make()
            obj.queue = self._make_nosleep_queue()
            reporter = self._make_reporter(report_at=1234.0, ident=ident)
            obj.reporters.add(reporter)
            obj.run(time=lambda: 1234.1)
        finally:
            end_queue.put(None)  # Let the thread end.
        th.join()

        self.assertEqual(len(self.reported), 1)
        report_time, frame = self.reported[0]
        self.assertEqual(report_time, 1234.1)
        self.assertIsNotNone(frame)
        self.assertIsNotNone(frame.f_code.co_filename)
        self.assertIsNotNone(frame.f_code.co_name)

        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0][1]
        self.assertEqual(t, 10.0)

    def test_run_with_broken_reporter(self):
        obj = self._make()
        obj.queue = self._make_nosleep_queue()

        reporter = self._make_reporter(report_at=1234.0,
                                       report_error=ValueError('synthetic'))
        obj.reporters.add(reporter)

        obj.run(time=lambda: 1234.0)

        self.assertEqual(self.reported, [(1234.0, None)])

        self.assertEqual(len(self.queue_gets), 1)
        t = self.queue_gets[0][1]
        self.assertEqual(t, 10.0)

    def test_run_when_timeout_reached(self):
        from slowlog.compat import Empty
        queue_gets = []
        queue_contents = [Empty(), None]

        class DummyQueue:
            def empty(self):
                return True

            def get(self, block, timeout):
                queue_gets.append((block, timeout))
                item = queue_contents.pop(0)
                if item is None:
                    return None
                else:
                    raise item

        obj = self._make()
        obj.queue = DummyQueue()

        reporter = self._make_reporter(report_at=1234.0)
        obj.reporters.add(reporter)

        obj.run(time=lambda: 1234.0)

        self.assertEqual(self.reported, [(1234.0, None)])
        self.assertEqual(queue_gets, [(True, 10.0), (True, 10.0)])


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

    def test_delete_monitor_on_stop(self):
        monitor = self._call()
        monitor.queue.put(None)
        monitor.join()
        from slowlog.monitor import _monitor
        self.assertIsNone(_monitor)
