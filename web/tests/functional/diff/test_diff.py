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

from codechecker_client.cmd_line_client import get_diff_remote_run_local_dir

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

    def test_1(self):

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
        report_filter.reviewStatus = \
                [ReviewStatus.CONFIRMED, ReviewStatus.UNREVIEWED]
        reports, _, _ = get_diff_remote_run_local_dir(
                self._cc_client, report_filter, DiffType.UNRESOLVED, [],
                ["run1"], [dir2], [])

        self.assertEqual(len(reports), 1)
        self.__remove_run(["run1"])
        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)

    def test_2(self):
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
        reports, _, _ = get_diff_remote_run_local_dir(
                self._cc_client, report_filter, DiffType.UNRESOLVED, [],
                ["run1"], [dir2], [])

        self.assertEqual(len(reports), 0)

        self.__remove_run(["run1"])
        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)
