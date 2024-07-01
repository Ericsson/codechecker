# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the GccAnalyzerResult, which
used in sequence transform gcc output to a plist file.
"""


import os
import plistlib
import shutil
import unittest

from codechecker_report_converter.analyzers.gcc import analyzer_result
from codechecker_report_converter.report.parser import plist

from libtest import env


OLD_PWD = None


class GCCAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the GccAnalyzerResult. """

    def setup_class(self):
        """ Initialize test files. """

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('gcc_parser')
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE
        self.test_workspace = os.environ['TEST_WORKSPACE']
        self.cc_result_dir = self.test_workspace

        self.analyzer_result = analyzer_result.AnalyzerResult()

        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'gcc_output_test_files')
        global OLD_PWD
        OLD_PWD = os.getcwd()
        os.chdir(os.path.join(os.path.dirname(__file__),
                              'gcc_output_test_files'))

    def teardown_class(self):
        """Clean up after the test."""

        global OLD_PWD
        os.chdir(OLD_PWD)

        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def test_no_plist_file(self):
        """ Test transforming single plist file. """
        analyzer_output_file = os.path.join(self.test_files, 'files',
                                            'double_free.cpp')

        ret = self.analyzer_result.transform(
            [analyzer_output_file], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")
        self.assertFalse(ret)

    def test_no_plist_dir(self):
        """ Test transforming single plist file. """
        analyzer_output_file = os.path.join(self.test_files, 'non_existing')

        ret = self.analyzer_result.transform(
            [analyzer_output_file], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")
        self.assertFalse(ret)

    def test_gcc_transform_single_file(self):
        """ Test transforming single plist file. """
        analyzer_output_file = os.path.join(
            self.test_files, 'double_free.cpp.sarif')
        self.analyzer_result.transform(
            [analyzer_output_file], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")

        plist_file = os.path.join(self.cc_result_dir,
                                  'double_free.cpp_gcc.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/double_free.cpp'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"
            print(
                res["diagnostics"][0]["issue_hash_content_of_line_in_context"])

        plist_file = os.path.join(self.test_files,
                                  'double_free.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
