# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests transforming Cargo Clippy JSON output to CodeChecker plist.
"""

import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.clippy import analyzer_result
from codechecker_report_converter.report.parser import plist


class ClippyAnalyzerResultTestCase(unittest.TestCase):
    """
    Test the output of the Clippy AnalyzerResult.
    """

    def setUp(self):
        """
        Setup test files.
        """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'clippy_output_test_files')

    def tearDown(self):
        """
        Clean temporary directory.
        """
        shutil.rmtree(self.cc_result_dir)

    def test_no_json_file(self):
        """
        Test transforming a non-json file.
        """
        result = os.path.join(self.test_files, 'Cargo.toml')

        ret = self.analyzer_result.transform(
            [result], self.cc_result_dir, plist.EXTENSION,
            file_name='{source_file}_{analyzer}')

        self.assertFalse(ret)

    def test_transform_dir(self):
        """
        Test transforming a directory.
        """
        ret = self.analyzer_result.transform(
            [self.test_files], self.cc_result_dir, plist.EXTENSION,
            file_name='{source_file}_{analyzer}')

        self.assertFalse(ret)

    def test_transform_single_file(self):
        """
        Test transforming Cargo JSON diagnostics.
        """
        result = os.path.join(self.test_files, 'all.json')

        self.analyzer_result.transform(
            [result], self.cc_result_dir, plist.EXTENSION,
            file_name='{source_file}_{analyzer}')

        plist_file = os.path.join(self.cc_result_dir, 'lib.rs_clippy.plist')
        with open(plist_file, mode='rb') as plist_stream:
            res = plistlib.load(plist_stream)

        res['files'][0] = os.path.join('src', 'lib.rs')
        self.assertTrue(res['metadata']['generated_by']['version'])
        res['metadata']['generated_by']['version'] = 'x.y.z'

        expected_plist = os.path.join(self.test_files, 'all.expected.plist')
        with open(expected_plist, mode='rb') as plist_stream:
            exp = plistlib.load(plist_stream)

        self.assertEqual(res, exp)

        reports = self.analyzer_result.get_reports(result)
        self.assertEqual(
            [report.severity for report in reports],
            ['LOW', 'LOW', 'CRITICAL'])

    def test_missing_source_file_is_skipped(self):
        """
        Test skipping a diagnostic that refers to a missing source file.
        """
        result = os.path.join(self.test_files, 'missing-source.json')

        reports = self.analyzer_result.get_reports(result)

        self.assertEqual(reports, [])

    def test_valid_json_non_objects_are_ignored(self):
        """
        Test skipping valid JSON lines that are not cargo objects.
        """
        result = os.path.join(self.test_files, 'edge-cases.json')

        reports = self.analyzer_result.get_reports(result)

        self.assertEqual(len(reports), 3)

    def test_non_dict_diagnostic_message_is_skipped(self):
        """
        Test skipping cargo compiler messages with malformed diagnostics.
        """
        result = os.path.join(self.test_files, 'edge-cases.json')

        reports = self.analyzer_result.get_reports(result)

        self.assertNotIn('not a diagnostic object',
                         [report.message for report in reports])

    def test_no_code_error_uses_rustc_group(self):
        """
        Test assigning no-code errors to the rustc checker group.
        """
        result = os.path.join(self.test_files, 'edge-cases.json')

        reports = self.analyzer_result.get_reports(result)
        report = next(report for report in reports
                      if report.message == 'could not compile fixture')

        self.assertEqual(report.checker_name, 'rustc')
        self.assertEqual(report.severity, 'CRITICAL')

    def test_no_code_warning_uses_clippy_group(self):
        """
        Test assigning no-code warnings to the clippy checker group.
        """
        result = os.path.join(self.test_files, 'edge-cases.json')

        reports = self.analyzer_result.get_reports(result)
        report = next(report for report in reports
                      if report.message == 'clippy warning without a code')

        self.assertEqual(report.checker_name, 'clippy')
        self.assertEqual(report.severity, 'LOW')

    def test_duplicate_notes_are_removed(self):
        """
        Test filtering duplicate notes from span and child diagnostics.
        """
        result = os.path.join(self.test_files, 'edge-cases.json')

        reports = self.analyzer_result.get_reports(result)
        report = next(report for report in reports
                      if report.message == 'diagnostic with duplicate notes')

        self.assertEqual(len(report.notes), 1)
        self.assertEqual(report.notes[0].message, 'duplicate note')


if __name__ == '__main__':
    unittest.main()
