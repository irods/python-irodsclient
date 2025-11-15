#!/usr/bin/env python

"""
NOTE: "If a test package name (directory with __init__.py) matches the pattern
       then the package will be checked for a load_tests function. If this
       exists then it will be called with loader, tests, pattern."
"""


import argparse
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

parser = argparse.ArgumentParser()

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

    parser.add_argument('--tests', '-t',
                    metavar='TESTS',
                    dest='tests',
                    nargs='+',
                    help='List of tests to run.')

    parser.add_argument('--environment_variable', '-e',
                    metavar='ENVIRONMENT_VARIABLE',
                    dest='env_var',
                    type=str,
                    help='Name of environment variable name to scan for in reason strings when filtering skipped test names to be output.')

    parser.add_argument('--output_tests_skipped', '-s',
                    metavar='SKIPPED_TESTS_OUTPUT_FILENAME',
                    dest='skipped_tests_output_filename',
                    type=str,
                    help='Name of a file into which to write names  of skipped tests.')

    parser.add_argument('--tests_file', '-f',
                    metavar='TESTS_FILE',
                    dest='tests_file',
                    help='Name of a file containing a list of tests to run.')

    args = parser.parse_args()

    if args.tests_file:
        if args.tests:
            print ('Cannot specify both --tests and --tests_file', file = sys.stderr)
            exit(2)
        args.tests = filter(None,open(args.tests_file).read().split("\n"))

    loader = TestLoader()

    if args.tests:
        suite = TestSuite(loader.loadTestsFromNames(args.tests))
    else:
        suite = TestSuite(loader.discover(start_dir = script_dir, pattern = '*_test.py', top_level_dir = script_dir))

    result = xmlrunner.XMLTestRunner(
        verbosity=2, output="/tmp/python-irodsclient/test-reports"
    ).run(suite)

    if args.skipped_tests_output_filename:
        with open(args.skipped_tests_output_filename,'w') as skip_file:
            do_output = (lambda reason: (args.env_var in reason) if args.env_var
                else True)
            for testinfo, reason in result.skipped:
                if do_output(reason):
                    print(testinfo.test_id, file=skip_file)

    if result.wasSuccessful():
        sys.exit(0)

    sys.exit(1)
