# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the RuffAnalyzerResult, which
used in sequence transform ruff output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.ruff import analyzer_result
from codechecker_report_converter.report.parser import plist


class RuffAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the RuffAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'ruff_output_test_files')

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_no_json_file(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'files',
                                       'simple.py')

        ret = self.analyzer_result.transform(
            [analyzer_result], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")
        self.assertFalse(ret)

    def test_transform_dir(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files)

        ret = self.analyzer_result.transform(
            [analyzer_result], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")
        self.assertFalse(ret)

    def test_transform_single_file(self):
        """ Test transforming single json file. """
        analyzer_result = os.path.join(self.test_files, 'simple.json')
        self.analyzer_result.transform(
            [analyzer_result], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")

        plist_file = os.path.join(self.cc_result_dir,
                                  'simple.py_ruff.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = os.path.join('files', 'simple.py')

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'simple.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)


if __name__ == '__main__':
    unittest.main()
