# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the CppcheckAnalyzerResult, which
used in sequence transform Cppcheck output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.cppcheck import analyzer_result
from codechecker_report_converter.report.parser import plist


OLD_PWD = None


def setup_module():
    """ Setup the test. """
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'cppcheck_output_test_files'))


def teardown_module():
    """ Restore environment after tests have ran. """
    global OLD_PWD
    os.chdir(OLD_PWD)


class CppcheckAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the CppcheckAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'cppcheck_output_test_files')

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_no_plist_file(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'files',
                                       'divide_zero.cpp')

        ret = self.analyzer_result.transform(
            analyzer_result, self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")
        self.assertFalse(ret)

    def test_no_plist_dir(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'non_existing')

        ret = self.analyzer_result.transform(
            analyzer_result, self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")
        self.assertFalse(ret)

    def test_transform_single_file(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(
            self.test_files, 'out', 'divide_zero.plist')
        self.analyzer_result.transform(
            analyzer_result, self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")

        plist_file = os.path.join(self.cc_result_dir,
                                  'divide_zero.cpp_cppcheck.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/divide_zero.cpp'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'divide_zero.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)

    def test_transform_directory(self):
        """ Test transforming a directory of plist files. """
        analyzer_result = os.path.join(self.test_files, 'out')
        self.analyzer_result.transform(
            analyzer_result, self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")

        plist_file = os.path.join(self.cc_result_dir,
                                  'divide_zero.cpp_cppcheck.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/divide_zero.cpp'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'divide_zero.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
