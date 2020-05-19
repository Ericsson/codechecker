# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the ESLintAnalyzerResult, which
used in sequence transform ESLint output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.eslint.analyzer_result import \
    ESLintAnalyzerResult


class ESLintAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the ESLintAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = ESLintAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'eslint_output_test_files')

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_no_json_file(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'files',
                                       'index.js')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_transform_dir(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files)

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_transform_single_file(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'reports.json')
        self.analyzer_result.transform(analyzer_result, self.cc_result_dir)

        plist_file = os.path.join(self.cc_result_dir,
                                  'index.js_eslint.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = os.path.join('files', 'index.js')

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'reports.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
