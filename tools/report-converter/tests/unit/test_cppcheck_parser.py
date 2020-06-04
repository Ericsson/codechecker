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

from codechecker_report_converter.cppcheck.analyzer_result import \
    CppcheckAnalyzerResult


class CppcheckAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the CppcheckAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = CppcheckAnalyzerResult()
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

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_no_plist_dir(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'non_existing')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_transform_single_file(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'divide_zero.plist')
        self.analyzer_result.transform(analyzer_result, self.cc_result_dir)

        plist_file = os.path.join(self.cc_result_dir,
                                  'divide_zero_cppcheck.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'divide_zero.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)

    def test_transform_directory(self):
        """ Test transforming a directory of plist files. """
        analyzer_result = os.path.join(self.test_files)
        self.analyzer_result.transform(analyzer_result, self.cc_result_dir)

        plist_file = os.path.join(self.cc_result_dir,
                                  'divide_zero_cppcheck.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'divide_zero.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
