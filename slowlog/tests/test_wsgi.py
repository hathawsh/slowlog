
"""Tests of slowlog.wsgi"""

import os
import sys
import tempfile
import time

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestFrameStatsApp(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.wsgi import FrameStatsApp
        return FrameStatsApp

    def _make(self, app_error=None, statsd_uri='statsd://localhost:9999'):
        self.ops = ops = []

        def dummy_app(environ, start_response):
            ops.append(('handle', environ, start_response))
            if app_error is not None:
                raise app_error
            else:
                return ['ok']

        class DummyMonitor:
            def add(self, reporter):
                ops.append(('add', reporter))

            def remove(self, reporter):
                ops.append(('remove', reporter))

        obj = self._class(dummy_app, statsd_uri)
        obj.get_monitor = DummyMonitor
        return obj

    def test_ctor(self):
        obj = self._make()
        self.assertEqual(obj.timeout, 2.0)
        self.assertEqual(obj.interval, 1.0)

    def test_call_without_app_error(self):
        obj = self._make()
        env = {}
        start_response = object()
        response = obj(env, start_response)
        self.assertEqual(response, ['ok'])
        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.framestats import FrameStatsReporter
        self.assertIsInstance(self.ops[0][1], FrameStatsReporter)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], env)
        self.assertIs(self.ops[1][2], start_response)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])

    def test_call_with_app_error(self):
        obj = self._make(app_error=ValueError('synthetic'))
        env = {}
        start_response = object()
        with self.assertRaises(ValueError):
            obj(env, start_response)

        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.framestats import FrameStatsReporter
        self.assertIsInstance(self.ops[0][1], FrameStatsReporter)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], env)
        self.assertIs(self.ops[1][2], start_response)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])


class Test_make_framestats(unittest.TestCase):

    def _call(self, next_app, _globals, **kw):
        from slowlog.wsgi import make_framestats
        return make_framestats(next_app, _globals, **kw)

    def test_it(self):
        def dummy_app(environ, start_response):
            pass

        obj = self._call(dummy_app, {}, interval='0.02',
                         statsd_uri='statsd://localhost:9999')
        self.assertIs(obj.next_app, dummy_app)
        self.assertEqual(obj.timeout, 2.0)
        self.assertEqual(obj.interval, 0.02)


class TestSlowLogApp(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.wsgi import SlowLogApp
        return SlowLogApp

    def _make(self, app_error=None, **kw):
        self.ops = ops = []

        def dummy_app(environ, start_response):
            ops.append(('handle', environ, start_response))
            if app_error is not None:
                raise app_error
            else:
                return ['ok']

        class DummyMonitor:
            def add(self, reporter):
                ops.append(('add', reporter))

            def remove(self, reporter):
                ops.append(('remove', reporter))

        obj = self._class(dummy_app, **kw)
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
            obj = self._make(timeout=1.9, interval=0.25, logfile=fn)
            self.assertEqual(obj.timeout, 1.9)
            self.assertEqual(obj.interval, 0.25)
            self.assertEqual(obj.log.name, 'slowlog')
            self.assertTrue(obj.log.handlers)
        finally:
            os.remove(fn)

    def test_call_without_app_error(self):
        obj = self._make()
        env = {}
        start_response = object()
        response = obj(env, start_response)
        self.assertEqual(response, ['ok'])
        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.wsgi import SlowRequestLogger
        self.assertIsInstance(self.ops[0][1], SlowRequestLogger)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], env)
        self.assertIs(self.ops[1][2], start_response)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])

    def test_call_with_app_error(self):
        obj = self._make(app_error=ValueError('synthetic'))
        env = {}
        start_response = object()
        with self.assertRaises(ValueError):
            obj(env, start_response)

        self.assertEqual(len(self.ops), 3)

        self.assertEqual(self.ops[0][0], 'add')
        from slowlog.wsgi import SlowRequestLogger
        self.assertIsInstance(self.ops[0][1], SlowRequestLogger)

        self.assertEqual(self.ops[1][0], 'handle')
        self.assertIs(self.ops[1][1], env)
        self.assertIs(self.ops[1][2], start_response)

        self.assertEqual(self.ops[2][0], 'remove')
        self.assertIs(self.ops[0][1], self.ops[2][1])


class Test_make_slowlog(unittest.TestCase):

    def _call(self, *args, **kw):
        from slowlog.wsgi import make_slowlog
        return make_slowlog(*args, **kw)

    def test_it(self):
        def dummy_app(environ, start_response):
            pass

        obj = self._call(dummy_app, {}, interval='0.02')
        self.assertIs(obj.next_app, dummy_app)
        self.assertEqual(obj.timeout, 2.0)
        self.assertEqual(obj.interval, 0.02)
        self.assertEqual(obj.hide_env, ['HTTP_COOKIE',
                                        'paste.cookies',
                                        'beaker.session'])


class TestSlowRequestLogger(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.wsgi import SlowRequestLogger
        return SlowRequestLogger

    def _make(self, ident=None, frame_limit=100):
        self.logged = logged = []

        class DummyLogger:
            def warning(self, msg, *args):
                logged.append(msg % args)

        class DummyApp:
            interval = 5.0
            hide_env = ('paste.cookies', 'HTTP_COOKIE')
            log = DummyLogger()

            def __init__(self):
                self.frame_limit = frame_limit

        app = DummyApp()
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff',
                   'QUERY_STRING': 'x=1',
                   'paste.cookies': []}
        start = time.time()
        report_at = start + 30.0
        return self._class(app, environ, start, report_at, ident)

    def test_ctor_with_default_ident(self):
        obj = self._make()
        from slowlog.compat import get_ident
        self.assertEqual(obj.ident, get_ident())

    def test_ctor_with_specified_ident(self):
        obj = self._make(ident=543)
        self.assertEqual(obj.ident, 543)

    def test_call_with_first_report(self):
        obj = self._make()
        obj(123456789.0)
        self.assertEqual(len(self.logged), 1)
        self.assertIn('POST http://example.com/stuff?x=1', self.logged[0])
        self.assertIn('<hidden>', self.logged[0])
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
        from slowlog.wsgi import Hidden
        return Hidden

    def test_it(self):
        self.assertEqual(repr(self._class()), '<hidden>')


class Test_construct_url(unittest.TestCase):

    def _call(self, *args, **kw):
        from slowlog.wsgi import construct_url
        return construct_url(*args, **kw)

    def test_with_public_host_and_default_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'me.com',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'http://me.com/stuff')

    def test_with_public_host_and_specified_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'me.com:80',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'http://me.com/stuff')

    def test_with_public_host_and_alt_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'me.com:81',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'http://me.com:81/stuff')

    def test_with_ssl_host(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'me.com',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'https://me.com/stuff')

    def test_with_ssl_host_and_specified_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'me.com:443',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'https://me.com/stuff')

    def test_with_ssl_host_and_alt_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'me.com:8443',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'https://me.com:8443/stuff')

    def test_with_public_server_name_and_default_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'http://example.com/stuff')

    def test_with_public_server_name_and_alt_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '81',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'http://example.com:81/stuff')

    def test_with_ssl_server_name_and_default_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '443',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'https://example.com/stuff')

    def test_with_ssl_server_name_and_specified_port(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8443',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'https://example.com:8443/stuff')

    def test_with_other_protocol(self):
        environ = {'REQUEST_METHOD': 'POST',
                   'wsgi.url_scheme': 'ftp',
                   'HTTP_HOST': 'me.com:2121',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '21',
                   'PATH_INFO': '/stuff'}
        self.assertEqual(self._call(environ), 'ftp://me.com:2121/stuff')
