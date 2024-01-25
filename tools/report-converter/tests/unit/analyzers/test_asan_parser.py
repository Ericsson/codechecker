# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform AddressSanitizer output to a plist file.
"""

import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.sanitizers.address import \
    analyzer_result, parser
from codechecker_report_converter.report.parser import plist

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__), 'asan_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class ASANAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the ASANAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.parser = parser.Parser()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_asan(self):
        """ Test for the asan.plist file. """
        self.analyzer_result.transform(
            ['asan.out'], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")

        with open('asan.plist', mode='rb') as pfile:
            exp = plistlib.load(pfile)

        plist_file = os.path.join(self.cc_result_dir, 'asan.cpp_asan.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/asan.cpp'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)

    def test_asan_checker_deduction(self):
        self.assertEqual(
            self.parser.deduce_checker_name(
                "heap-use-after-free on address 0x614000000044 at "
                "pc 0x0000004f4b45 bp 0x7ffd40559120 sp 0x7ffd40559118"),
            "AddressSanitizer.generic-error")

        self.assertEqual(
            self.parser.deduce_checker_name(
                "heap-use-after-free on address  at "
                "pc 0x0000004f4b45 bp 0x7ffd40559120 sp 0x7ffd40559118"),
            "AddressSanitizer.generic-error")

        self.assertEqual(
            self.parser.deduce_checker_name(
                "HURR DURR YOUR CODE BAD SHAME ON YOU"),
            "AddressSanitizer")
