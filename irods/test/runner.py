#!/usr/bin/env python

"""
NOTE: "If a test package name (directory with __init__.py) matches the pattern
       then the package will be checked for a load_tests function. If this
       exists then it will be called with loader, tests, pattern."
"""


import os
import sys
from unittest import TestLoader, TestSuite
import xmlrunner
import logging

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
h = logging.StreamHandler()
f = logging.Formatter(
    "%(asctime)s %(name)s-%(levelname)s [%(pathname)s %(lineno)d] %(message)s"
)
h.setFormatter(f)
logger.addHandler(h)

def abs_path(initial_dir, levels_up = 0):
    directory = initial_dir
    while levels_up > 0:
        levels_up -= 1
        directory = os.path.join(directory,'..')
    return os.path.abspath(directory)

# Load all tests in the current directory and run them.
if __name__ == "__main__":

    # Get path to script directory for test import and/or discovery.
    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

    # Must set the path for the imported tests.
    sys.path.insert(0, abs_path(script_dir, levels_up = 2))

    loader = TestLoader()
    if sys.argv[1:]:
        suite = TestSuite(loader.loadTestsFromNames(sys.argv[1:]))
    else:
        suite = TestSuite(loader.discover(start_dir = script_dir, pattern = '*_test.py', top_level_dir = script_dir))

    result = xmlrunner.XMLTestRunner(
        verbosity=2, output="/tmp/python-irodsclient/test-reports"
    ).run(suite)
    if result.wasSuccessful():
        sys.exit(0)

    sys.exit(1)
