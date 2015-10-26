#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import unittest
import argparse
import logging

def get_logger(verbosity):
    test_logger = logging.getLogger('unittest_runner')
    stream_handler = logging.StreamHandler()
    test_logger.addHandler(stream_handler)
    test_logger.setLevel(logging.INFO)
    if verbosity > 1:
        test_logger.setLevel(logging.DEBUG)
    return test_logger

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Python unit test runner')

    parser.add_argument('-v', action="store_true", default=False,
                        dest='verbosity',
                        help='set verbosity level for the unit test runner')

    options = parser.parse_args()

    verbosity = 1
    if options.verbosity:
        verbosity = 2

    log = get_logger(verbosity)

    script_dir = os.path.dirname(os.path.realpath(__file__))

    unit_tests_dir = os.path.join(script_dir, 'tests', 'unit_test')

    log.debug('Loading unit tests from: ' + unit_tests_dir)

    test_loader = unittest.TestLoader()

    suite = test_loader.discover(start_dir=unit_tests_dir)

    alltests = unittest.TestSuite((suite))

    unittest.TextTestRunner(verbosity=verbosity).run(alltests)
