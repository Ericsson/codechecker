# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the LCOV AnalyzerResult, which
transforms LCOV tracefiles to a CodeChecker coverage file.
"""

import os
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.lcov import analyzer_result
from codechecker_report_converter.report import coverage, report_file


class LcovAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the LCOV AnalyzerResult. """

    def setUp(self):
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(
            os.path.dirname(__file__), 'lcov_output_test_files')

    def tearDown(self):
        shutil.rmtree(self.cc_result_dir)

    def __transform(
        self,
        *file_names: str
    ) -> dict[str, coverage.FileCoverage]:
        """ Transform the given test files and read the result. """
        ret = self.analyzer_result.transform(
            [os.path.join(self.test_files, f) for f in file_names],
            self.cc_result_dir, 'plist')
        self.assertTrue(ret)

        return coverage.read(
            coverage.get_coverage_file_path(self.cc_result_dir))

    def test_transform_simple(self):
        """ Test transforming a tracefile with only line records. """
        result = self.__transform('simple.info')

        hello = result['/home/user/project/hello.c']
        self.assertEqual(hello.covered_lines, [3, 4, 6, 8, 10])
        self.assertEqual(hello.uncovered_lines, [5])
        self.assertEqual(hello.functions_found, 0)

        utils = result['/home/user/project/utils.c']
        self.assertEqual(utils.covered_lines, [1, 2, 7, 11])
        self.assertEqual(utils.uncovered_lines, [5, 9])
        self.assertEqual(utils.lines_found, 6)
        self.assertEqual(utils.lines_hit, 4)

    def test_transform_lcov2_function_records(self):
        """ Test the FNL/FNA records written by LCOV 2.2 and newer. """
        result = self.__transform('lcov2.info')

        main = result['/home/user/project/main.c']
        self.assertEqual(main.covered_lines, [5, 6, 7, 9, 10, 11, 12])
        self.assertEqual(main.uncovered_lines, [2, 3, 8])
        self.assertEqual(main.functions_found, 3)
        self.assertEqual(main.functions_hit, 2)

    def test_transform_lcov1_function_records(self):
        """
        Test the FN/FNDA records of LCOV 1.x, DA records with checksum and
        the fallback to the FNF/FNH summary records. Branch records must be
        ignored.
        """
        result = self.__transform('lcov1_part1.info')

        hello = result['/home/user/project/hello.c']
        self.assertEqual(hello.covered_lines, [3, 4])
        self.assertEqual(hello.uncovered_lines, [5, 12, 13])
        self.assertEqual(hello.functions_found, 2)
        self.assertEqual(hello.functions_hit, 1)

        utils = result['/home/user/project/utils.c']
        self.assertEqual(utils.functions_found, 4)
        self.assertEqual(utils.functions_hit, 3)

    def test_merge_multiple_tracefiles(self):
        """
        Execution counts of the same source file in multiple tracefiles are
        summed up. Malformed records are skipped.
        """
        result = self.__transform('lcov1_part1.info', 'lcov1_part2.info')

        hello = result['/home/user/project/hello.c']
        self.assertEqual(hello.covered_lines, [3, 4, 12])
        self.assertEqual(hello.uncovered_lines, [5, 13])
        self.assertEqual(hello.functions_found, 2)
        self.assertEqual(hello.functions_hit, 2)

    def test_relative_source_path(self):
        """ Relative source paths are resolved against the working dir. """
        info_file = os.path.join(self.cc_result_dir, 'relative.info')
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write("SF:src/a.c\nDA:1,1\n")

        ret = self.analyzer_result.transform(
            [info_file], self.cc_result_dir, 'plist')
        self.assertTrue(ret)

        result = coverage.read(
            coverage.get_coverage_file_path(self.cc_result_dir))
        self.assertEqual(list(result), [os.path.abspath('src/a.c')])

    def __transform_text(
        self,
        content: str
    ) -> dict[str, coverage.FileCoverage]:
        """ Transform the given tracefile content and read the result. """
        info_file = os.path.join(self.cc_result_dir, 'input.info')
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(content)

        out_dir = os.path.join(self.cc_result_dir, 'out')
        self.assertTrue(self.analyzer_result.transform(
            [info_file], out_dir, 'plist'))

        return coverage.read(coverage.get_coverage_file_path(out_dir))

    def test_negative_and_huge_counts(self):
        """
        Negative execution counts (written by some gcov versions because of
        counter overflow) are handled as not executed. Huge counts don't
        overflow.
        """
        result = self.__transform_text(
            "SF:/src/a.c\n"
            "FN:1,f\n"
            "FN:5,g\n"
            "FNDA:-3,f\n"
            "FNDA:18446744073709551615,g\n"
            "DA:1,-1\n"
            "DA:2,18446744073709551615\n"
            "DA:3,99999999999999999999999\n"
            "end_of_record\n")

        a = result['/src/a.c']
        self.assertEqual(a.covered_lines, [2, 3])
        self.assertEqual(a.uncovered_lines, [1])
        self.assertEqual(a.functions_found, 2)
        self.assertEqual(a.functions_hit, 1)

    def test_values_out_of_storable_range(self):
        """
        Line numbers which can not be stored by the server are ignored and
        function counts are limited, so the output is always valid.
        """
        result = self.__transform_text(
            "SF:/src/a.c\n"
            "DA:1,1\n"
            "DA:4294967296,1\n"
            "FNF:99999999999\n"
            "FNH:99999999999\n"
            "end_of_record\n")

        a = result['/src/a.c']
        self.assertEqual(a.covered_lines, [1])
        self.assertEqual(a.functions_found, coverage.MAX_VALUE)
        self.assertEqual(a.functions_hit, coverage.MAX_VALUE)

    def test_missing_end_of_record(self):
        """
        A new 'SF' record starts a new source file even if the previous one
        was not closed by 'end_of_record'. The last record of the file may
        be unclosed too.
        """
        result = self.__transform_text(
            "SF:/src/a.c\n"
            "DA:1,1\n"
            "SF:/src/b.c\n"
            "DA:1,0\n"
            "DA:2,3\n")

        self.assertEqual(result['/src/a.c'].covered_lines, [1])
        self.assertEqual(result['/src/a.c'].uncovered_lines, [])
        self.assertEqual(result['/src/b.c'].covered_lines, [2])
        self.assertEqual(result['/src/b.c'].uncovered_lines, [1])

    def test_repeated_source_file_in_one_tracefile(self):
        """
        Records of the same source file in one tracefile are merged, e.g.
        when 'lcov --add-tracefile' was not used to combine test runs.
        """
        result = self.__transform_text(
            "SF:/src/a.c\nDA:1,0\nDA:2,0\nFN:1,f\nFNDA:0,f\nend_of_record\n"
            "SF:/src/a.c\nDA:1,2\nDA:3,0\nFNDA:1,f\nend_of_record\n")

        a = result['/src/a.c']
        self.assertEqual(a.covered_lines, [1])
        self.assertEqual(a.uncovered_lines, [2, 3])
        self.assertEqual((a.functions_found, a.functions_hit), (1, 1))

    def test_function_records_with_end_line_and_commas(self):
        """
        'FN' records may contain the end line of the function (LCOV 2.0) and
        function names may contain commas (e.g. C++ signatures).
        """
        result = self.__transform_text(
            "SF:/src/a.cpp\n"
            "FN:3,9,main\n"
            "FN:11,foo(int, int)\n"
            "FNDA:2,main\n"
            "FNDA:0,foo(int, int)\n"
            "FNF:2\n"
            "FNH:1\n"
            "end_of_record\n")

        a = result['/src/a.cpp']
        self.assertEqual((a.functions_found, a.functions_hit), (2, 1))
        self.assertEqual(a.lines_found, 0)

    def test_records_outside_of_source_file(self):
        """ Records which don't belong to an 'SF' record are ignored. """
        result = self.__transform_text(
            "DA:1,1\n"
            "end_of_record\n"
            "SF:/src/a.c\n"
            "DA:0,1\n"
            "DA:x,1\n"
            "DA:2\n"
            "DA:3,1\n"
            "end_of_record\n"
            "DA:4,1\n")

        self.assertEqual(list(result), ['/src/a.c'])
        self.assertEqual(result['/src/a.c'].covered_lines, [3])
        self.assertEqual(result['/src/a.c'].uncovered_lines, [])

    def test_transform_empty_file(self):
        """ Transforming an empty tracefile produces no output. """
        ret = self.analyzer_result.transform(
            [os.path.join(self.test_files, 'empty.info')],
            self.cc_result_dir, 'plist')
        self.assertFalse(ret)
        self.assertFalse(os.path.exists(
            coverage.get_coverage_file_path(self.cc_result_dir)))

    def test_transform_missing_file(self):
        """ A missing tracefile is reported, not a crash. """
        ret = self.analyzer_result.transform(
            [os.path.join(self.test_files, 'missing.info')],
            self.cc_result_dir, 'plist')
        self.assertFalse(ret)

    def test_no_analyzer_result_files_created(self):
        """
        The output directory must not contain files which would be parsed as
        analyzer results by 'CodeChecker parse' or 'CodeChecker store'.
        """
        self.__transform('simple.info')

        for root, _, files in os.walk(self.cc_result_dir):
            for f in files:
                self.assertFalse(report_file.is_supported(
                    os.path.join(root, f)))

    def test_get_reports_returns_empty(self):
        """ Coverage converters don't produce Report objects. """
        info_file = os.path.join(self.test_files, 'simple.info')
        self.assertEqual(self.analyzer_result.get_reports(info_file), [])


if __name__ == '__main__':
    unittest.main()
