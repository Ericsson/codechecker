# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the LCOV AnalyzerResult, which
transforms LCOV .info files to a coverage JSON file.
"""

import json
import os
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.lcov import analyzer_result


class LcovAnalyzerResultTestCase(unittest.TestCase):
    """Test the output of the LCOV AnalyzerResult."""

    def setUp(self):
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(
            os.path.dirname(__file__), 'lcov_output_test_files')

    def tearDown(self):
        shutil.rmtree(self.cc_result_dir)

    def test_transform_single_info_file(self):
        """Test transforming a single LCOV .info file."""
        info_file = os.path.join(self.test_files, 'simple.info')
        ret = self.analyzer_result.transform(
            [info_file], self.cc_result_dir, 'plist')
        self.assertTrue(ret)

        out_path = os.path.join(
            self.cc_result_dir, 'coverage', 'coverage.json')
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, 'r') as f:
            data = json.load(f)

        hello_key = os.path.abspath('/home/user/project/hello.c')
        utils_key = os.path.abspath('/home/user/project/utils.c')

        self.assertIn(hello_key, data)
        self.assertIn(utils_key, data)

        # hello.c: covered=[3,4,6,8,10], uncovered=[5]
        self.assertEqual(data[hello_key]['lines'], [3, 4, 6, 8, 10])
        self.assertEqual(data[hello_key]['uncovered'], [5])
        # utils.c: covered=[1,2,7,11], uncovered=[5,9]
        self.assertEqual(data[utils_key]['lines'], [1, 2, 7, 11])
        self.assertEqual(data[utils_key]['uncovered'], [5, 9])

    def test_transform_empty_file(self):
        """Test transforming an empty .info file produces no output."""
        info_file = os.path.join(self.test_files, 'empty.info')
        ret = self.analyzer_result.transform(
            [info_file], self.cc_result_dir, 'plist')
        self.assertFalse(ret)

    def test_get_reports_returns_empty(self):
        """Coverage converters don't produce Report objects."""
        info_file = os.path.join(self.test_files, 'simple.info')
        reports = self.analyzer_result.get_reports(info_file)
        self.assertEqual(reports, [])

    def test_tool_name(self):
        """Verify the tool name for CLI registration."""
        self.assertEqual(
            analyzer_result.AnalyzerResult.TOOL_NAME, 'lcov')


if __name__ == '__main__':
    unittest.main()
