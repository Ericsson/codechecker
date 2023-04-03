#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test review status functionality."""


import datetime
import logging
import os
import shutil
import time
import unittest

from typing import Callable, List

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentKind, \
    DetectionStatus, Order, ReviewStatus, ReviewStatusRule, \
    ReviewStatusRuleFilter, ReviewStatusRuleSortMode, \
    ReviewStatusRuleSortType, RunFilter, DiffType, ReportFilter

from codechecker_client.cmd_line_client import \
    get_diff_local_dirs, get_diff_remote_run_local_dir, \
    get_diff_local_dir_remote_run, get_diff_remote_runs

from libtest import env, codechecker, plist_test, project
from libtest.thrift_client_to_db import get_all_run_results


class TestReviewStatus(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

    def tearDown(self):
        """ Remove all review status rules after each test cases. """
        self.__remove_all_rules()

    def __remove_all_rules(self):
        """ Removes all review status rules from the database. """
        self._cc_client.removeReviewStatusRules(None)

        # Check that there is no review status rule in the database.
        self.assertFalse(self._cc_client.getReviewStatusRulesCount(None))

        rules = self._cc_client.getReviewStatusRules(None, None, None, 0)
        self.assertFalse(rules)

    def __analyze(self, file_dir, source_code):
        """
        """
        build_json_path = os.path.join(file_dir, "build.json")

        build_json = f"""
[{{
    "directory": "{file_dir}",
    "file": "main.c",
    "command": "gcc main.c -o /dev/null"
}}]
"""
        os.makedirs(file_dir, exist_ok=True)

        with open(os.path.join(file_dir, "main.c"), "w") as f:
            f.write(source_code)

        with open(build_json_path, "w") as f:
            f.write(build_json)

        codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        codechecker_cfg["workspace"] = file_dir
        codechecker_cfg["reportdir"] = os.path.join(file_dir, "reports")
        codechecker_cfg['analyzers'] = ['clangsa', 'clang-tidy']

        codechecker.analyze(codechecker_cfg, file_dir)

    def __analyze_and_store(self, file_dir, store_name, source_code):
        """
        """
        self.__analyze(file_dir, source_code)

        codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        codechecker_cfg["workspace"] = file_dir
        codechecker_cfg["reportdir"] = \
            os.path.join(file_dir, "reports")
        codechecker.store(codechecker_cfg, store_name)

    def __get_run_id(self, run_name):
        runs = self._cc_client.getRunData(None, None, 0, None)
        self.assertEqual(len(runs), 1)
        test_run = [run for run in runs if run.name == run_name]
        self.assertEqual(len(test_run), 1)
        return test_run[0].runid

    def __remove_run(self, run_names):
        run_filter = RunFilter()
        run_filter.names = run_names
        ret = self._cc_client.removeRun(None, run_filter)
        self.assertTrue(ret)

    #===-------------------------------------------------------------------===#
    # Local-local tests.
    #===-------------------------------------------------------------------===#

    def test_local_local(self):
        # Diff two different, local runs.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""

        src_nullptr_deref = """
void b() {
  int *i = 0;
  *i = 5;
}
"""
        self.__analyze(dir1, src_div_by_zero)
        self.__analyze(dir2, src_nullptr_deref)

        # We set no review statuses via //codechecker-suppress, so the report
        # must be unreviewed.
        report_filter = ReportFilter()
        report_filter.reviewStatus = [ReviewStatus.UNREVIEWED]

        def get_run_diff_count(diff_type: DiffType):
            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir1], [], [dir2], [])
            return len(reports)

        # b() is a new report.
        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)

        # a() is the old report.
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)

        # There are no common reports.
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)

    def test_local_local_identical(self):
        # Diff two identical, local runs.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze(dir1, src_div_by_zero)
        self.__analyze(dir2, src_div_by_zero)

        # We set no review statuses via //codechecker-suppress, so the report
        # must be unreviewed.
        report_filter = ReportFilter()
        report_filter.reviewStatus = [ReviewStatus.UNREVIEWED]

        def get_run_diff_count(diff_type: DiffType):
            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir1], [], [dir2], [])
            return len(reports)

        # No new reports appeared.
        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)

        # No reports disappeared.
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)

        # There is a single report that has remained.
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 1)

        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)

    def test_localFPAnnotated_local_identical(self):
        # Diff identical, local runs, where the baseline report is suppressed
        # via //codechecker_suppress.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero_FP = """
void a() {
  int i = 0;
  // codechecker_suppress [all] SUPPRESS ALL
  (void)(10 / i);
}
"""
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze(dir1, src_div_by_zero_FP)
        self.__analyze(dir2, src_div_by_zero)

        def get_run_diff_count(diff_type: DiffType,
                               review_statuses: List[ReviewStatus]):
            report_filter = ReportFilter()
            report_filter.reviewStatus = review_statuses

            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir1], [], [dir2], [])
            return len(reports)

        # No new reports appeared.
        self.assertEqual(
                get_run_diff_count(DiffType.NEW, [ReviewStatus.UNREVIEWED,
                                                  ReviewStatus.FALSE_POSITIVE,
                                                  ReviewStatus.INTENTIONAL,
                                                  ReviewStatus.CONFIRMED]), 0)

        # No new reports appeared.
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED,
                                            [ReviewStatus.UNREVIEWED,
                                             ReviewStatus.FALSE_POSITIVE,
                                             ReviewStatus.INTENTIONAL,
                                             ReviewStatus.CONFIRMED]), 0)

        # Although we set a review status in the baseline, the new run is not
        # annotated. Statuses from source code annotations should not carry
        # over from one local directory to another.
        # You could think of this as someone removed the suppression, and the
        # report reappeared as non-reviewed.
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED,
                                            [ReviewStatus.UNREVIEWED]), 1)

        self.assertEqual(get_run_diff_count(DiffType.RESOLVED,
                                            [ReviewStatus.FALSE_POSITIVE,
                                             ReviewStatus.INTENTIONAL,
                                             ReviewStatus.CONFIRMED]), 0)

        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)

    #===-------------------------------------------------------------------===#
    # Local-Remote tests.
    #===-------------------------------------------------------------------===#

    def test_local_remote(self):

        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze_and_store(dir1, "run1", src_div_by_zero)
        self.__analyze(dir2, src_div_by_zero)

        report_filter = ReportFilter()
        report_filter.reviewStatus = [ReviewStatus.UNREVIEWED]

        diff_type = DiffType.UNRESOLVED

        reports, _, _ = get_diff_remote_run_local_dir(
                self._cc_client, report_filter, diff_type, [],
                ["run1"], [dir2], [])

        self.assertEqual(len(reports), 1)
        self.__remove_run(["run1"])
        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)

    def test_local_remoteReviewStatusRule(self):
        # Create two identical runs, store one on the server, leave one
        # locally.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze_and_store(dir1, "run1", src_div_by_zero)
        self.__analyze(dir2, src_div_by_zero)

        # Add a "false positive" review status rule on the stored report.
        results = get_all_run_results(self._cc_client)
        self.assertEqual(len(results), 1)

        self._cc_client.addReviewStatusRule(
                results[0].bugHash, ReviewStatus.FALSE_POSITIVE, "")

        # Even though the local report is not marked as a false positive, we
        # expect the review status rule on the server to affect it.
        report_filter = ReportFilter()
        report_filter.reviewStatus = \
                [ReviewStatus.CONFIRMED, ReviewStatus.UNREVIEWED]

        diff_type = DiffType.NEW

        reports, _, _ = get_diff_remote_run_local_dir(
                self._cc_client, report_filter, diff_type, [],
                ["run1"], [dir2], [])

        self.assertEqual(len(reports), 0)

        self.__remove_run(["run1"])
        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)
