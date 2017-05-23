#!/usr/bin/env python

"""
NOTE: "If a test package name (directory with __init__.py) matches the pattern
       then the package will be checked for a load_tests function. If this
       exists then it will be called with loader, tests, pattern."
"""

from __future__ import absolute_import
import os
import sys
from unittest import TestLoader, TestSuite
import xmlrunner
import logging

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
h = logging.StreamHandler()
f = logging.Formatter("%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s")
h.setFormatter(f)
logger.addHandler(h)


# Load all tests in the current directory and run them
if __name__ == "__main__":
    # must set the path for the imported tests
    sys.path.insert(0, os.path.abspath('../..'))

    loader = TestLoader()
    suite = TestSuite(loader.discover(start_dir='.', pattern='*_test.py',
                                      top_level_dir="."))

    result = xmlrunner.XMLTestRunner(
        verbosity=2, output='/tmp/python-irodsclient/test-reports').run(suite)
    if result.wasSuccessful():
        sys.exit(0)

    sys.exit(1)
