# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Tests for reading and writing the coverage file of report dirs. """

import json
import os
import shutil
import tempfile
import unittest

from codechecker_report_converter.report import coverage


class CoverageFileTestCase(unittest.TestCase):
    """ Test the coverage file reader and writer. """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def __write_raw(self, data) -> str:
        path = os.path.join(self.tmp_dir, 'coverage.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        return path

    def test_coverage_file_location(self):
        """ The location is part of the client-server contract. """
        self.assertEqual(
            coverage.get_coverage_file_path('/reports'),
            os.path.join('/reports', 'coverage', 'coverage.json'))

    def test_write_and_read(self):
        """ The written data can be read back. """
        path = coverage.get_coverage_file_path(self.tmp_dir)
        coverage.write(path, {
            '/src/a.c': coverage.FileCoverage([3, 1], [2], 2, 1)}, 'lcov')

        result = coverage.read(path)
        self.assertEqual(result, {
            '/src/a.c': coverage.FileCoverage([1, 3], [2], 2, 1)})
        self.assertEqual(result['/src/a.c'].lines_found, 3)
        self.assertEqual(result['/src/a.c'].lines_hit, 2)

    def test_write_and_read_branch_mcdc_region(self):
        """ The optional branch, MC/DC and region data can be read back. """
        path = coverage.get_coverage_file_path(self.tmp_dir)
        cov = coverage.FileCoverage(
            [1], [2], 1, 1,
            branches_found=4, branches_hit=3,
            mcdc_found=2, mcdc_hit=1,
            regions_found=5, regions_hit=4,
            line_branches=[[2, 1, 2], [1, 2, 2]],
            line_mcdc=[[1, 1, 2, ['C2']]],
            uncovered_regions=[[2, 3, 2, 9], [1, 1, 1, 4], [1, 1, 1, 4]])
        coverage.write(path, {'/src/a.c': cov}, 'llvm-cov')

        result = coverage.read(path)['/src/a.c']
        self.assertEqual((result.branches_found, result.branches_hit),
                         (4, 3))
        self.assertEqual((result.mcdc_found, result.mcdc_hit), (2, 1))
        self.assertEqual((result.regions_found, result.regions_hit), (5, 4))
        self.assertEqual(result.line_branches, [[1, 2, 2], [2, 1, 2]])
        self.assertEqual(result.line_mcdc, [[1, 1, 2, ['C2']]])
        self.assertEqual(result.uncovered_regions,
                         [[1, 1, 1, 4], [2, 3, 2, 9]])

    def test_missing_optional_keys(self):
        """
        Files written before the branch, MC/DC and region keys were added
        are valid: the metrics were not measured.
        """
        path = self.__write_raw({
            "version": 1, "tool": "lcov",
            "files": {"/a.c": {"covered_lines": [1], "uncovered_lines": [2],
                               "functions_found": 1, "functions_hit": 1}}})
        result = coverage.read(path)['/a.c']
        self.assertEqual(result, coverage.FileCoverage([1], [2], 1, 1))
        self.assertEqual(result.branches_found, 0)
        self.assertEqual(result.line_mcdc, [])

        # Metrics which were not measured are not written.
        out_path = os.path.join(self.tmp_dir, 'out.json')
        coverage.write(out_path, {'/a.c': result}, 'lcov')
        with open(out_path, encoding='utf-8') as f:
            self.assertEqual(set(json.load(f)['files']['/a.c']), {
                "covered_lines", "uncovered_lines", "functions_found",
                "functions_hit"})

    def test_covered_line_wins(self):
        """ A line listed both as covered and uncovered is covered. """
        result = coverage.parse({
            "version": 1,
            "files": {"/a.c": {"covered_lines": [1, 2],
                               "uncovered_lines": [2, 3]}}})
        self.assertEqual(result['/a.c'].covered_lines, [1, 2])
        self.assertEqual(result['/a.c'].uncovered_lines, [3])

    def test_invalid_data(self):
        """ Malformed data raises CoverageFileError. """
        invalid = [
            [],
            {"files": {}},
            {"version": 2, "files": {}},
            {"version": 1, "files": []},
            {"version": 1, "files": {"/a.c": []}},
            {"version": 1, "files": {"": {}}},
            {"version": 1, "files": {"/a.c": {"covered_lines": [0]}}},
            {"version": 1, "files": {"/a.c": {"covered_lines": [-1]}}},
            {"version": 1, "files": {"/a.c": {"covered_lines": ["1"]}}},
            {"version": 1, "files": {"/a.c": {"covered_lines": [True]}}},
            {"version": 1, "files": {"/a.c": {"uncovered_lines": 5}}},
            {"version": 1, "files": {"/a.c": {"functions_found": -1}}},
            {"version": 1, "files": {"/a.c": {"functions_found": 1,
                                              "functions_hit": 2}}},
            {"version": 1, "files": {"/a.c": {"covered_lines": [2**31]}}},
            {"version": 1, "files": {"/a.c": {"functions_found": 2**31}}},
            {"version": 1, "files": {"/a.c": {"branches_hit": 1}}},
            {"version": 1, "files": {"/a.c": {"mcdc_found": -1}}},
            {"version": 1, "files": {"/a.c": {"regions_found": 1,
                                              "regions_hit": 2}}},
            {"version": 1, "files": {"/a.c": {"line_branches": {}}}},
            {"version": 1, "files": {"/a.c": {"line_branches": [[1, 2]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_branches": [[1, 3, 2]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_branches": [[0, 1, 2]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_branches": [[1, 1, 2], [1, 0, 2]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_mcdc": [[1, 1, 2]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_mcdc": [[1, 1, 2, "C1"]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_mcdc": [[1, 1, 2, [1]]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_mcdc": [[1, 3, 2, []]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_mcdc": [[1, 1, 2, ["x" * 257]]]}}},
            {"version": 1, "files": {"/a.c": {
                "line_mcdc": [[1, 1, 2, ["C"] * 65]]}}},
            {"version": 1, "files": {"/a.c": {
                "uncovered_regions": [[1, 1, 1]]}}},
            {"version": 1, "files": {"/a.c": {
                "uncovered_regions": [[1, 0, 1, 2]]}}},
            {"version": 1, "files": {"/a.c": {
                "uncovered_regions": [[2, 1, 1, 5]]}}},
            {"version": 1, "files": {"/a.c": {
                "uncovered_regions": [[1, 5, 1, 4]]}}},
            {"version": 1, "files": {"/a.c": {
                "uncovered_regions": [[1, 1, 1, 2**31]]}}},
        ]
        for data in invalid:
            with self.subTest(data=data):
                with self.assertRaises(coverage.CoverageFileError):
                    coverage.parse(data)

    def test_unknown_file(self):
        """
        Files of other tools are reported with UnknownCoverageFileError, so
        'CodeChecker store' can skip them instead of failing.
        """
        for data in [[], {}, {"meta": {"version": "7.6"}, "files": {}}]:
            with self.subTest(data=data):
                with self.assertRaises(coverage.UnknownCoverageFileError):
                    coverage.parse(data)

        with self.assertRaises(coverage.UnknownCoverageFileError):
            coverage.read(self.__write_raw({"files": {}}))

        # A file with our 'version' key is recognized, so its errors are
        # real errors.
        for data in [{"version": 2, "files": {}}, {"version": 1}]:
            with self.subTest(data=data):
                try:
                    coverage.parse(data)
                except coverage.UnknownCoverageFileError:
                    self.fail("Recognized file reported as unknown.")
                except coverage.CoverageFileError:
                    pass

    def test_max_values(self):
        """ Values which fit in the 32-bit database columns are accepted. """
        result = coverage.parse({
            "version": 1,
            "files": {"/a.c": {"covered_lines": [coverage.MAX_VALUE],
                               "functions_found": coverage.MAX_VALUE,
                               "functions_hit": coverage.MAX_VALUE}}})
        self.assertEqual(result['/a.c'].covered_lines, [coverage.MAX_VALUE])

    def test_read_errors(self):
        """ Unreadable files raise CoverageFileError. """
        with self.assertRaises(coverage.CoverageFileError):
            coverage.read(os.path.join(self.tmp_dir, 'missing.json'))

        with self.assertRaises(coverage.CoverageFileError):
            coverage.read(self.__write_raw("{not json"))

        with self.assertRaises(coverage.CoverageFileError):
            coverage.read(self.__write_raw({"version": 1}))

    def test_unknown_keys_are_ignored(self):
        """ Unknown keys are ignored for forward compatibility. """
        result = coverage.read(self.__write_raw({
            "version": 1, "tool": "x", "extra": 1,
            "files": {"/a.c": {"covered_lines": [1], "regions": []}}}))
        self.assertEqual(result['/a.c'].covered_lines, [1])
