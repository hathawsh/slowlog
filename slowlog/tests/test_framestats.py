
try:
    import unittest2 as unittest
except ImportError:
    import unittest


class Test_report_framestats(unittest.TestCase):

    def _call(self, client, frame):
        from slowlog.framestats import report_framestats
        return report_framestats(client, frame)

    def _make_statsd_client(self):
        self.sentbufs = sentbufs = []

        class DummyStatsdClient:
            def incr(self, name, amount, buf):
                buf.append('%s:%s|c' % (name, amount))

            def sendbuf(self, buf):
                sentbufs.append('\n'.join(buf))

        return DummyStatsdClient()

    def _make_frame_stack(self, length):
        class DummyCode:
            def __init__(self, i):
                self.co_name = 'dummy_name_%d' % i

        class DummyFrame:
            f_back = None

            def __init__(self, i):
                self.f_code = DummyCode(i)
                self.f_globals = {'__name__': 'dummy.module%d' % i}
                self.f_locals = {}

        current_frame = None
        f = None

        while length:
            f_back = DummyFrame(length)
            if current_frame is None:
                f = current_frame = f_back
            else:
                f.f_back = f_back
                f = f_back
            length -= 1

        return current_frame

    def test_with_empty_frame(self):
        client = self._make_statsd_client()
        self._call(client, None)
        self.assertEqual(len(self.sentbufs), 0)

    def test_with_short_stack(self):
        client = self._make_statsd_client()
        frame = self._make_frame_stack(3)
        self._call(client, frame)
        self.assertEqual(len(self.sentbufs), 1)
        expect = ['framestats.dummy.module3.dummy_name_3:1|c',
                  'framestats._.dummy_module3_dummy_name_3:1|c',
                  'framestats.dummy.module2.dummy_name_2:0.667|c',
                  'framestats._.dummy_module2_dummy_name_2:0.667|c',
                  'framestats.dummy.module1.dummy_name_1:0.333|c',
                  'framestats._.dummy_module1_dummy_name_1:0.333|c',
                  ]
        self.assertEqual(self.sentbufs[0].splitlines(), expect)

    def test_with_barrier(self):
        client = self._make_statsd_client()
        frame = self._make_frame_stack(4)
        frame.f_back.f_locals['__slowlog_barrier__'] = True
        self._call(client, frame)
        self.assertEqual(len(self.sentbufs), 1)
        expect = ['framestats.dummy.module4.dummy_name_4:1|c',
                  'framestats._.dummy_module4_dummy_name_4:1|c',
                  'framestats.dummy.module3.dummy_name_3:0.5|c',
                  'framestats._.dummy_module3_dummy_name_3:0.5|c',
                  ]
        self.assertEqual(expect, self.sentbufs[0].splitlines())

    def test_with_long_stack(self):
        client = self._make_statsd_client()
        frame = self._make_frame_stack(20)
        self._call(client, frame)
        self.assertEqual(len(self.sentbufs), 2)
        # Send innermost frames first because they are probably more
        # important.
        self.assertIn('framestats.dummy.module20.dummy_name_20:1|c',
                      self.sentbufs[0])
        self.assertIn('framestats.dummy.module1.dummy_name_1:0.05|c',
                      self.sentbufs[1])

    def test_with_frame_lacking_module_name(self):
        # Skip over frames that don't have a module name.
        client = self._make_statsd_client()
        frame = self._make_frame_stack(3)
        frame.f_back.f_globals = {}
        self._call(client, frame)
        self.assertEqual(len(self.sentbufs), 1)
        expect = ['framestats.dummy.module3.dummy_name_3:1|c',
                  'framestats._.dummy_module3_dummy_name_3:1|c',
                  'framestats.(module).dummy_name_2:0.667|c',
                  'framestats._.(module)_dummy_name_2:0.667|c',
                  'framestats.dummy.module1.dummy_name_1:0.333|c',
                  'framestats._.dummy_module1_dummy_name_1:0.333|c',
                  ]
        self.assertEqual(self.sentbufs[0].splitlines(), expect)


class TestFrameStatsReporter(unittest.TestCase):

    @property
    def _class(self):
        from slowlog.framestats import FrameStatsReporter
        return FrameStatsReporter

    def test_ctor_with_default_ident(self):
        from slowlog.compat import get_ident

        client = object()
        obj = self._class(client, 123456789, 1.5)
        self.assertEqual(obj.report_at, 123456789)
        self.assertEqual(obj.interval, 1.5)
        self.assertEqual(obj.ident, get_ident())

    def test_ctor_with_specified_ident(self):
        client = object()
        obj = self._class(client, 123456789, 1.5, ident=54321)
        self.assertEqual(obj.report_at, 123456789)
        self.assertEqual(obj.interval, 1.5)
        self.assertEqual(obj.ident, 54321)

    def test_call_without_frame(self):
        client = object()
        obj = self._class(client, 123456789.0, 1.5)
        obj(123456789.0)

    def test_call_with_frame(self):
        reported = []

        def report_framestats(client, frame, limit):
            reported.append((client, frame, limit))

        client = object()
        reporter = self._class(client, 123456789.0, 1.5)
        frame = object()
        reporter(123456789.0, frame, report_framestats=report_framestats)
        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0], (client, frame, 100))
