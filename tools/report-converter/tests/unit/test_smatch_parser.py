# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the SmatchAnalyzerResult, which
used in sequence transform Smatch output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest


from codechecker_report_converter.smatch.analyzer_result import \
    SmatchAnalyzerResult


class SmatchAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the SmatchAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = SmatchAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'smatch_output_test_files')

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_no_smatch_output_file(self):
        """ Test transforming single C file. """
        analyzer_result = os.path.join(self.test_files, 'files',
                                       'sample.c')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_transform_dir(self):
        """ Test transforming a directory. """
        analyzer_result = os.path.join(self.test_files)

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_transform_single_file(self):
        """ Test transforming single output file. """
        analyzer_result = os.path.join(self.test_files, 'sample.out')
        self.analyzer_result.transform(analyzer_result, self.cc_result_dir)

        plist_file = os.path.join(self.cc_result_dir,
                                  'sample.c_smatch.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = os.path.join('files', 'sample.c')

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'sample.expected.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
