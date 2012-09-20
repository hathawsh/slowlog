
"""Tests of the slowlog module"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class Test_includeme(unittest.TestCase):

    def _call(self, config):
        from slowlog import includeme
        includeme(config)

    def _make_config(self, settings=None):
        self.added_tweens = added_tweens = []

        class DummyRegistry:
            def __init__(self):
                self.settings = settings or {}

        class DummyConfig:
            registry = DummyRegistry()

            def add_tween(self, name):
                added_tweens.append(name)

        return DummyConfig()

    def test_with_defaults(self):
        config = self._make_config()
        self._call(config)
        self.assertEqual(self.added_tweens, [])

    def test_with_slowlog_enabled(self):
        config = self._make_config(settings={'slowlog': 'true'})
        self._call(config)
        self.assertEqual(self.added_tweens, ['slowlog.tween.SlowLogTween'])

    def test_with_framestats_enabled(self):
        config = self._make_config(settings={'framestats': 'true'})
        self._call(config)
        self.assertEqual(self.added_tweens, ['slowlog.tween.FrameStatsTween'])

    def test_with_both_enabled(self):
        config = self._make_config(settings={'framestats': 'true',
                                             'slowlog': 'true'})
        self._call(config)
        self.assertEqual(self.added_tweens, ['slowlog.tween.SlowLogTween',
                                             'slowlog.tween.FrameStatsTween'])
