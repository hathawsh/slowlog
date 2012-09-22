
from slowlog.compat import StringIO
import sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class Test_print_stack(unittest.TestCase):

    def _call(self, frame, limit, outfile):
        from slowlog.exc import print_stack
        print_stack(frame, limit, outfile)

    def test_with_barrier(self):
        frames = []

        def func3():
            frames.append(sys._getframe())

        def func2():
            func3()

        def func1():
            __slowlog_barrier__ = True
            func2()

        func1()
        frame = frames[0]
        f = StringIO()
        self._call(frame, 100, f)
        lines = f.getvalue().splitlines()
        self.assertEqual(len(lines), 6)
        match = self.assertRegexpMatches
        match(lines[0], r'  File ".*/test_exc.py", line \d+, in func1$')
        match(lines[2], r'  File ".*/test_exc.py", line \d+, in func2$')
        match(lines[4], r'  File ".*/test_exc.py", line \d+, in func3$')

    def test_without_barrier(self):
        frame = sys._getframe()
        f = StringIO()
        self._call(frame, 100, f)
        lines = f.getvalue().splitlines()
        self.assertGreater(len(lines), 2)
        self.assertLess(len(lines), 100)
