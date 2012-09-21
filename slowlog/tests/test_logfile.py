
"""Tests of slowlog.logfile"""

import tempfile
import os
import logging

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class Test_make_file_logger(unittest.TestCase):

    def _call(self, filename):
        from slowlog.logfile import make_file_logger
        return make_file_logger(filename)

    def test_with_filename(self):
        f = tempfile.NamedTemporaryFile(delete=False)
        fn = f.name
        f.close()
        try:
            logger = self._call(fn)
            logger.info('Hello!')
            f = open(fn, 'r')
            content = f.read()
            f.close()
            self.assertRegexpMatches(content.rstrip(),
                                     r'\d{4}-\d{2}-\d{2} '
                                     r'\d{2}:\d{2}:\d{2},\d{3} - Hello!$')
        finally:
            os.remove(fn)

    def test_with_logger(self):
        logfile = logging.Logger('test')
        self.assertIs(self._call(logfile), logfile)

    def test_with_handler(self):
        logfile = logging.StreamHandler()
        logger = self._call(logfile)
        self.assertIs(logger.handlers[0], logfile)

    def test_with_open_file(self):
        from slowlog.compat import StringIO
        logfile = StringIO()
        logger = self._call(logfile)
        self.assertIs(logger.handlers[0].stream, logfile)
