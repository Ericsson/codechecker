# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the llvm-cov AnalyzerResult, which
transforms 'llvm-cov export' JSON files to a CodeChecker coverage file.
"""

import json
import os
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.llvm_cov import analyzer_result
from codechecker_report_converter.report import coverage, report_file


def _export(files=None, functions=None,
            export_type=analyzer_result.EXPORT_TYPE):
    return {"type": export_type, "version": "2.0.1",
            "data": [{"files": files or [], "functions": functions or []}]}


class LlvmCovAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the llvm-cov AnalyzerResult. """

    def setUp(self):
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(
            os.path.dirname(__file__), 'llvm_cov_output_test_files')

    def tearDown(self):
        shutil.rmtree(self.cc_result_dir)

    def __transform(self, *paths: str) -> dict[str, coverage.FileCoverage]:
        ret = self.analyzer_result.transform(
            list(paths), self.cc_result_dir, 'plist')
        self.assertTrue(ret)

        return coverage.read(
            coverage.get_coverage_file_path(self.cc_result_dir))

    def __write(self, data, name='export.json') -> str:
        path = os.path.join(self.cc_result_dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        return path

    def test_transform_clang_export(self):
        """
        Test an export of Clang 20 with '-fcoverage-mcdc'. The line coverage
        must be the same as reported by 'llvm-cov report' (26/21).
        """
        result = self.__transform(
            os.path.join(self.test_files, 'calc.json'))

        calc = result['/home/user/project/calc.c']
        self.assertEqual((calc.lines_found, calc.lines_hit), (26, 21))
        self.assertEqual(calc.uncovered_lines, [9, 17, 22, 23, 24])
        self.assertEqual((calc.functions_found, calc.functions_hit), (4, 3))
        self.assertEqual((calc.regions_found, calc.regions_hit), (20, 17))
        self.assertEqual((calc.branches_found, calc.branches_hit), (12, 8))
        self.assertEqual((calc.mcdc_found, calc.mcdc_hit), (4, 1))

        self.assertEqual(calc.line_branches,
                         [[5, 3, 4], [7, 2, 4], [14, 2, 2], [16, 1, 2]])
        self.assertEqual(calc.line_mcdc,
                         [[5, 1, 2, ['C1']], [7, 0, 2, ['C1', 'C2']]])
        self.assertEqual(calc.uncovered_regions,
                         [[9, 3, 9, 11], [17, 5, 17, 14], [22, 1, 24, 2]])

    def test_line_counts(self):
        """ Port of LLVM's LineCoverageStats. """
        segments = [
            # Region entry with count on line 1, wraps to line 2 and 3.
            [1, 1, 5, True, True, False],
            # Gap region on line 3 doesn't start a region.
            [3, 4, 0, True, False, True],
            # Line 4 is wrapped by the gap segment: count 0.
            # Skipped region (no count, region entry) on line 5.
            [5, 1, 0, False, True, False],
            # Line 6-7: wrapped segment without count: not executable.
            [8, 1, 0, True, True, False],
            [8, 5, 7, True, True, False],
            [8, 9, 0, False, False, False],
        ]
        self.assertEqual(analyzer_result.get_line_counts(segments),
                         {1: 5, 2: 5, 3: 5, 4: 0, 8: 7})

        self.assertEqual(analyzer_result.get_line_counts([]), {})
        self.assertEqual(analyzer_result.get_line_counts(
            [[0, 1, 1, True, True, False], "x", [2, 1]]), {})

    def test_template_instances(self):
        """
        A region which occurs in multiple functions (template instances) is
        uncovered only if it was never executed in any of them.
        """
        functions = [
            {"filenames": ["/src/t.h"], "regions": [
                [1, 1, 3, 2, 0, 0, 0, 0],
                [2, 3, 2, 9, 0, 0, 0, 0],
                # Gap region, not a code region.
                [2, 10, 2, 12, 0, 0, 0, 3]]},
            {"filenames": ["/src/other.h", "/src/t.h"], "regions": [
                [1, 1, 3, 2, 4, 1, 0, 0],
                [2, 3, 2, 9, 0, 1, 0, 0],
                # Region of another file.
                [5, 1, 5, 2, 0, 0, 0, 0]]},
        ]
        files = [{"filename": "/src/t.h", "segments": []}]
        result = self.__transform(self.__write(_export(files, functions)))

        self.assertEqual(result['/src/t.h'].uncovered_regions,
                         [[2, 3, 2, 9]])
        self.assertNotIn('/src/other.h', result)

    def test_merge_branches_and_mcdc(self):
        """
        Branches and MC/DC decisions of the same range are merged: a branch
        or condition is covered if it was covered by any of them. Other
        layouts of the MC/DC record (other LLVM versions) are accepted.
        """
        files = [{
            "filename": "/src/a.c",
            "branches": [[3, 5, 3, 9, 0, 1, 0, 0, 4],
                         [3, 5, 3, 9, 2, 0, 0, 0, 4],
                         [4, 5, 4, 9, 0, 0, 0, 0, 4],
                         [4, 5, 4, 9, "x", 0, 0, 0, 4]],
            "mcdc_records": [[3, 5, 3, 20, 0, 5, [True, False, False]],
                             [3, 5, 3, 20, [False, False, True]],
                             [3, 5, 3, 20, 0, 5, ["bad"]]],
            "summary": {"branches": {"count": 4, "covered": 2},
                        "mcdc": {"count": 3, "covered": 2},
                        "regions": {"count": 2, "covered": 7}}}]
        result = self.__transform(self.__write(_export(files)))

        a = result['/src/a.c']
        self.assertEqual(a.line_branches, [[3, 2, 2], [4, 0, 2]])
        self.assertEqual(a.line_mcdc, [[3, 2, 3, ['C2']]])
        self.assertEqual((a.branches_found, a.branches_hit), (4, 2))
        self.assertEqual((a.mcdc_found, a.mcdc_hit), (3, 2))
        # The hit count is limited by the found count.
        self.assertEqual((a.regions_found, a.regions_hit), (2, 2))

    def test_merge_multiple_exports(self):
        """ The same file in multiple exports is merged. """
        first = self.__write(_export([{
            "filename": "/src/a.c",
            "segments": [[1, 1, 0, True, True, False],
                         [1, 9, 0, False, False, False]],
            "summary": {"regions": {"count": 2, "covered": 0}}}]), 'a.json')
        second = self.__write(_export([{
            "filename": "/src/a.c",
            "segments": [[1, 1, 3, True, True, False],
                         [1, 9, 0, False, False, False]],
            "summary": {"regions": {"count": 2, "covered": 1}}}]), 'b.json')

        a = self.__transform(first, second)['/src/a.c']
        self.assertEqual(a.covered_lines, [1])
        self.assertEqual((a.regions_found, a.regions_hit), (2, 1))

    def test_multiple_exports_derive_counts_from_details(self):
        """
        If a file is in multiple exports (e.g. two test binaries covering
        different halves), the region, branch and MC/DC counts are derived
        from the merged details, because the summaries can't be merged.
        """
        def export(region_counts, branch_counts, conditions):
            files = [{
                "filename": "/src/a.c",
                "segments": [],
                "branches": [[1, 1, 1, 5] + branch_counts + [0, 0, 4],
                             [2, 1, 2, 5] + branch_counts[::-1] + [0, 0, 4]],
                "mcdc_records": [[1, 1, 1, 9, 0, 5, conditions]],
                "summary": {
                    "regions": {"count": 2, "covered": 1},
                    "branches": {"count": 4, "covered": 2},
                    "mcdc": {"count": 2, "covered": 1}}}]
            functions = [{
                "filenames": ["/src/a.c"],
                "regions": [[1, 1, 1, 9, region_counts[0], 0, 0, 0],
                            [2, 1, 2, 9, region_counts[1], 0, 0, 0]]}]
            return _export(files, functions)

        first = self.__write(export([1, 0], [1, 0], [True, False]), 'a.json')
        second = self.__write(export([0, 1], [0, 1], [False, True]), 'b.json')

        a = self.__transform(first, second)['/src/a.c']
        self.assertEqual((a.regions_found, a.regions_hit), (2, 2))
        self.assertEqual(a.uncovered_regions, [])
        self.assertEqual((a.branches_found, a.branches_hit), (4, 4))
        self.assertEqual((a.mcdc_found, a.mcdc_hit), (2, 2))

        # A single export keeps its summary.
        a = self.__transform(first)['/src/a.c']
        self.assertEqual((a.regions_found, a.regions_hit), (2, 1))
        self.assertEqual((a.branches_found, a.branches_hit), (4, 2))

    def test_malformed_values_are_ignored(self):
        """ Values of unexpected types are handled as empty lists. """
        data = {"type": analyzer_result.EXPORT_TYPE, "data": [
            {"files": {"x": 1}, "functions": "x"},
            {"files": [{"filename": "/src/a.c", "segments": 5,
                        "branches": {"a": 1}, "mcdc_records": "x",
                        "summary": []}],
             "functions": [{"filenames": 3, "regions": [1]},
                           {"filenames": ["/src/a.c"], "regions": 7}]}]}

        a = self.__transform(self.__write(data))['/src/a.c']
        self.assertEqual(a, coverage.FileCoverage())

    def test_not_an_export_file(self):
        """ Other JSON files produce no output and an error. """
        for data in ["{not json", [], {"type": "other", "data": []},
                     _export(export_type="llvm.coverage.json.other")]:
            with self.subTest(data=data):
                with self.assertLogs('report-converter', 'ERROR'):
                    ret = self.analyzer_result.transform(
                        [self.__write(data)], self.cc_result_dir, 'plist')
                self.assertFalse(ret)
                self.assertFalse(os.path.exists(
                    coverage.get_coverage_file_path(self.cc_result_dir)))

    def test_transform_missing_file(self):
        """ A missing export file is reported, not a crash. """
        self.assertFalse(self.analyzer_result.transform(
            [os.path.join(self.test_files, 'missing.json')],
            self.cc_result_dir, 'plist'))

    def test_no_analyzer_result_files_created(self):
        """ The output must not contain analyzer result files. """
        self.__transform(os.path.join(self.test_files, 'calc.json'))

        for root, _, files in os.walk(self.cc_result_dir):
            for f in files:
                self.assertFalse(report_file.is_supported(
                    os.path.join(root, f)))

    def test_get_reports_returns_empty(self):
        """ Coverage converters don't produce Report objects. """
        self.assertEqual(self.analyzer_result.get_reports(
            os.path.join(self.test_files, 'calc.json')), [])


if __name__ == '__main__':
    unittest.main()
