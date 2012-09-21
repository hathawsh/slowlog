
"""Tests of slowlog.tween"""
import os
import sys
import tempfile
import time

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestFrameStatsTween(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.tween import FrameStatsTween
        return FrameStatsTween

    def _make(self, settings=None, handler_error=None):
        self.ops = ops = []

        def dummy_handler(request):
            ops.append(('handle', request))
            if handler_error is not None:
                raise handler_error
            else:
                return 'ok'

        class DummyRegistry:
            def __init__(self):
                self.settings = settings or {'statsd_uri':
                                             'statsd://localhost:9999'}

        class DummyMonitor:
            def add(self, reporter):
                ops.append(('add', reporter))

            def remove(self, reporter):
                ops.append(('remove', reporter))

        obj = self._class(dummy_handler, DummyRegistry())
        obj.get_monitor = DummyMonitor
        return obj

    def test_ctor_with_default_settings(self):
        obj = self._make()
        self.assertEqual(obj.timeout, 2.0)
        self.assertEqual(obj.interval, 1.0)

    def test_ctor_with_custom_settings(self):
        obj = self._make(settings={'framestats_timeout': '2.1',
                                   'framestats_interval': '0.125',
                                   'statsd_uri': 'statsd://localhost:9999'})
        self.assertEqual(obj.timeout, 2.1)
        self.assertEqual(obj.interval, 0.125)

    def test_call_without_handler_error(self):
        obj = self._make()
        request = object()
        response = obj(request)
        self.assertEqual(response, 'ok')
        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.framestats import FrameStatsReporter
        self.assertIsInstance(self.ops[0][1], FrameStatsReporter)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], request)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])

    def test_call_with_handler_error(self):
        obj = self._make(handler_error=ValueError('synthetic'))
        request = object()
        with self.assertRaises(ValueError):
            obj(request)

        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.framestats import FrameStatsReporter
        self.assertIsInstance(self.ops[0][1], FrameStatsReporter)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], request)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])


class TestSlowLogTween(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.tween import SlowLogTween
        return SlowLogTween

    def _make(self, settings=None, handler_error=None):
        self.ops = ops = []

        def dummy_handler(request):
            ops.append(('handle', request))
            if handler_error is not None:
                raise handler_error
            else:
                return 'ok'

        class DummyRegistry:
            def __init__(self):
                self.settings = settings or {}

        class DummyMonitor:
            def add(self, reporter):
                ops.append(('add', reporter))

            def remove(self, reporter):
                ops.append(('remove', reporter))

        obj = self._class(dummy_handler, DummyRegistry())
        obj.get_monitor = DummyMonitor
        return obj

    def test_ctor_with_default_settings(self):
        obj = self._make()
        self.assertEqual(obj.timeout, 2.0)
        self.assertEqual(obj.interval, 1.0)
        self.assertEqual(obj.log.name, 'slowlog')
        self.assertFalse(obj.log.handlers)

    def test_ctor_with_custom_settings(self):
        f = tempfile.NamedTemporaryFile(delete=False)
        fn = f.name
        f.close()
        try:
            obj = self._make(settings={'slowlog_timeout': '2.1',
                                       'slowlog_interval': '0.125',
                                       'slowlog_file': fn})
            self.assertEqual(obj.timeout, 2.1)
            self.assertEqual(obj.interval, 0.125)
            self.assertEqual(obj.log.name, 'slowlog')
            self.assertTrue(obj.log.handlers)
        finally:
            os.remove(fn)

    def test_call_without_handler_error(self):
        obj = self._make()
        request = object()
        response = obj(request)
        self.assertEqual(response, 'ok')
        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.tween import TweenRequestLogger
        self.assertIsInstance(self.ops[0][1], TweenRequestLogger)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], request)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])

    def test_call_with_handler_error(self):
        obj = self._make(handler_error=ValueError('synthetic'))
        request = object()
        with self.assertRaises(ValueError):
            obj(request)

        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.tween import TweenRequestLogger
        self.assertIsInstance(self.ops[0][1], TweenRequestLogger)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], request)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])


class TestTweenRequestLogger(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.tween import TweenRequestLogger
        return TweenRequestLogger

    def _make(self, ident=None, method='POST', frame_limit=100):
        self.logged = logged = []

        class DummyLogger:
            def warning(self, msg, *args):
                logged.append(msg % args)

        class DummyTween:
            interval = 5.0
            hide_post_vars = ('password', 'HIDEME')
            log = DummyLogger()

            def __init__(self):
                self.frame_limit = frame_limit

        class DummyRequest:
            def __init__(self):
                self.method = method
                self.url = 'http://example.com/stuff?x=1'
                if method == 'POST':
                    self.POST = {'login': 'abc', 'password': '123'}
                else:
                    self.POST = {}

        tween = DummyTween()
        request = DummyRequest()
        start = time.time()
        report_at = start + 30.0
        return self._class(tween, request, start, report_at, ident)

    def test_ctor_with_default_ident(self):
        obj = self._make()
        from slowlog.compat import get_ident
        self.assertEqual(obj.ident, get_ident())

    def test_ctor_with_specified_ident(self):
        obj = self._make(ident=543)
        self.assertEqual(obj.ident, 543)

    def test_call_with_first_report_as_post(self):
        obj = self._make()
        obj(123456789.0)
        self.assertEqual(len(self.logged), 1)
        self.assertIn('POST http://example.com/stuff?x=1', self.logged[0])
        self.assertIn('<hidden>', self.logged[0])
        self.assertNotIn('Traceback:', self.logged[0])

    def test_call_with_first_report_as_get(self):
        obj = self._make(method='GET')
        obj(123456789.0)
        self.assertEqual(len(self.logged), 1)
        self.assertIn('GET http://example.com/stuff?x=1', self.logged[0])
        self.assertNotIn('<hidden>', self.logged[0])
        self.assertNotIn('Traceback:', self.logged[0])

    def test_call_with_subsequent_report(self):
        obj = self._make()
        obj.logged_first = True
        obj(123456789.0)
        self.assertEqual(len(self.logged), 1)
        self.assertIn('POST http://example.com/stuff?x=1', self.logged[0])
        self.assertNotIn('<hidden>', self.logged[0])
        self.assertNotIn('Traceback:', self.logged[0])

    def test_call_with_traceback_shown(self):
        obj = self._make()
        frame = sys._getframe()
        obj(123456789.0, frame)
        self.assertEqual(len(self.logged), 1)
        self.assertIn('POST http://example.com/stuff?x=1', self.logged[0])
        self.assertIn('Traceback:', self.logged[0])

    def test_call_with_traceback_hidden(self):
        obj = self._make(frame_limit=0)
        frame = sys._getframe()
        obj(123456789.0, frame)
        self.assertEqual(len(self.logged), 1)
        self.assertIn('POST http://example.com/stuff?x=1', self.logged[0])
        self.assertNotIn('Traceback:', self.logged[0])


class TestHidden(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.tween import Hidden
        return Hidden

    def test_it(self):
        self.assertEqual(repr(self._class()), '<hidden>')
