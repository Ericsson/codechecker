# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the PMDAnalyzerResult, which
transforms PMD JSON output into CodeChecker plist files.
"""

import os
import plistlib
import shutil
import tempfile
import unittest
import json

from codechecker_report_converter.analyzers.pmd import analyzer_result
from codechecker_report_converter.report.parser import plist


class PMDAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the PMDAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(
            os.path.dirname(__file__),
            'pmd_output_test_files'
        )

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_no_pmd_output_file(self):
        """ Test transforming a non-PMD file. Should return False. """
        analyzer_output = os.path.join(
            self.test_files, 'files', 'Main.java'
        )

        with self.assertRaises(json.JSONDecodeError):
            self.analyzer_result.transform(
                [analyzer_output],
                self.cc_result_dir,
                plist.EXTENSION,
                file_name="{source_file}_{analyzer}"
            )

    def test_transform_dir(self):
        """ Test transforming a directory instead of a file. Should return False. """
        analyzer_output = self.test_files

        with self.assertRaises(IsADirectoryError):
            self.analyzer_result.transform(
                [analyzer_output],
                self.cc_result_dir,
                plist.EXTENSION,
                file_name="{source_file}_{analyzer}"
            )

    def test_transform_single_file(self):
        analyzer_output = os.path.join(self.test_files, 'simple.json')

        java_file_src = os.path.join(self.test_files, 'files', 'Main.java')
        java_file_dst = os.path.join(self.cc_result_dir, 'Main.java')
        shutil.copy(java_file_src, java_file_dst)

        try:
            self.analyzer_result.transform(
                [analyzer_output],
                self.cc_result_dir,
                plist.EXTENSION,
                file_name="{source_file}_{analyzer}"
            )
        finally:
            os.remove(java_file_dst)

        plist_file = os.path.join(self.cc_result_dir, 'Main.java_pmd.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

        res['files'][0] = 'Main.java'
        for diag in res['diagnostics']:
            diag['location']['file'] = 'Main.java'
            diag.pop('issue_hash_content_of_line_in_context', None)
            diag.pop('issue_hash_keys', None)
            if 'severity' not in diag:
                diag['severity'] = 'warning'

        res['metadata']['generated_by']['version'] = "x.y.z"

        expected_plist = os.path.join(self.test_files, 'simple.expected.plist')
        with open(expected_plist, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res['files'], exp['files'])     
        
        self.assertEqual(len(res['diagnostics']), len(exp['diagnostics']))
        for rdiag, ediag in zip(res['diagnostics'], exp['diagnostics']):
            self.assertEqual(rdiag['category'], ediag['category'])
            self.assertEqual(rdiag['description'], ediag['description'])
            self.assertEqual(rdiag['location'], ediag['location'])
            self.assertEqual(rdiag['severity'], ediag['severity'])
            self.assertEqual(rdiag['check_name'], ediag['check_name'])
