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
import time
import unittest

from typing import Callable, List

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentKind, \
    DetectionStatus, Order, ReviewStatus, ReviewStatusRule, \
    ReviewStatusRuleFilter, ReviewStatusRuleSortMode, \
    ReviewStatusRuleSortType, RunFilter

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

        # Get the run names which belong to this test.
        run_names = env.get_run_names(self.test_workspace)
        # get the current run data
        run_filter = RunFilter(names=run_names, exactMatch=True)

        runs = self._cc_client.getRunData(run_filter, None, 0, None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test, '
                         'with the given name configured at the test init.')
        self._runid = test_runs[0].runId

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
        codechecker_cfg["reportdir"] = \
            os.path.join(file_dir, "reports")

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

    def test_review_and_detection_status_changes(self):

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

        args = []

        # we need to invoke codechecker cmd diff... ugh...
        reports, _, _ = get_diff_remote_run_local_dir(self._cc_client, \
                                                      ["run1"],\
                                                      [dir2], [])

        print(diff_res)
        # self.assertEqual(report.detectionStatus, DetectionStatus.NEW)
        # self.assertEqual(report.reviewData.status, ReviewStatus.FALSE_POSITIVE)
        # self.assertIsNotNone(report.fixedAt)
        # fixed_at_old = report.fixedAt
