
from setuptools import setup, find_packages
import os
import sys

requires = ['setuptools',
            'perfmetrics',
            ]

if sys.version_info[:2] < (2, 7):
    requires.append('unittest2')

here = os.path.dirname(__file__)
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

setup(name='slowlog',
      version='0.9',
      author='Shane Hathaway',
      author_email='shane@hathawaymix.org',
      description="Log and graph slow Pyramid and WSGI apps",
      long_description=README + '\n\n' + CHANGES,
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Developers",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 3",
                   "License :: Repoze Public License",
                   "Topic :: System :: Monitoring",
                   ],
      url="https://github.com/hathawsh/slowlog",
      license='BSD-derived (http://www.repoze.org/LICENSE.txt)',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      tests_require=requires + ['nose', 'pyramid'],
      test_suite="nose.collector",
      install_requires=requires,
      entry_points="""\
      [paste.filter_app_factory]
      slowlog = slowlog.wsgi:make_slowlog
      framestats = slowlog.wsgi:make_framestats
      """,
      )
