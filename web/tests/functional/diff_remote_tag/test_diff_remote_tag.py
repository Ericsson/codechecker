#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""diff_remote_tag function test.

Test the comparison of two remote (in the database) tags of the same run.
This test case was initially created to test whether diffing remote tags works
fine.
"""

import os
import sys
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CompareData, \
    DiffType, ReportFilter, RunHistoryFilter

from libtest import codechecker, env


class DiffRemoteTag(unittest.TestCase):

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        self.test_cfg = env.import_test_cfg(self.test_workspace)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._codechecker_cfg = self.test_cfg['codechecker_cfg']

        # Get the run names which belong to this test.
        run_names = env.get_run_names(self.test_workspace)
        self.assertEqual(1, len(run_names))
        self._run_name = run_names[0]

        self._base_report_dir = \
            self.test_cfg['test_project']['project_path_base']
        self._new_report_dir = \
            self.test_cfg['test_project']['project_path_new']

    def store(self, report_dir, tag):
        self._codechecker_cfg['reportdir'] = report_dir

        self._codechecker_cfg['tag'] = tag
        ret = codechecker.store(self._codechecker_cfg, self._run_name)
        if ret:
            sys.exit(1)
            return

    def test_get_diff_checker_counts(self):
        """
        Test diff result types for new results.
        """

        # Store two non-identical runs under the same name, but different tags.
        self.store(self._base_report_dir, 't1')
        self.store(self._new_report_dir, 't2')

        # Diff these two -- but first, extract the IDs of the run and the tags.
        runs = self._cc_client.getRunData(None, None, 0, None)
        self.assertEqual(len(runs), 1)
        self.test_run = [run for run in runs if run.name == self._run_name]

        # Got the run ID. Use it to get hold of the tag IDs.
        self._run_id = self.test_run[0].runId

        def get_run_tag_id(tag_name):
            run_history_filter = RunHistoryFilter(tagNames=[tag_name])
            tags = self._cc_client.getRunHistory([self._run_id], None, None,
                                                 run_history_filter)
            self.assertEqual(len(tags), 1)
            return tags[0].id

        # Got the tag IDs. In order to diff them against one another, we need
        # to create a ReportFilter for the base, and a CompareData for the new
        # run.
        base_tag_id = get_run_tag_id('t1')
        new_tag_id = get_run_tag_id('t2')

        base_tag_filter = ReportFilter(runTag=[base_tag_id])
        new_tag_cmp_data = CompareData(runIds=[self._run_id],
                                       diffType=DiffType.NEW,
                                       runTag=[new_tag_id])

        # First ---------------------------------------------------------------
        diff_res = self._cc_client.getCheckerCounts([self._run_id],
                                                    base_tag_filter,
                                                    new_tag_cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # core.CallAndMessage is only enabled in the new run.
        test_res = {"core.NullDereference": 4}
        self.assertDictEqual(diff_dict, test_res)

        # Second --------------------------------------------------------------
        # Now, store another run that doesn't have these new results with a
        # different tag. Here, we simply reuse the base run.
        self.store(self._base_report_dir, 't3')
        self.assertIsNotNone(new_tag_cmp_data)

        diff_res = self._cc_client.getCheckerCounts([self._run_id],
                                                    base_tag_filter,
                                                    new_tag_cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # This used to fail -- the query incorrectly removed reports whose
        # fixed_at date was set (and since the reports in t2 are not present
        # in t3, all those reports had it set), and diff_res was an empty dict.
        # FIXME: And still does.
        test_res = {}
        self.assertDictEqual(diff_dict, test_res)

        # Third ---------------------------------------------------------------
        new_tag_filter = ReportFilter(runTag=[new_tag_id])

        diff_res = self._cc_client.getCheckerCounts([self._run_id],
                                                    new_tag_filter,
                                                    None,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # Just some sanity check -- the diff may be incorrect, but t2 is still
        # on the server with all of its reports.
        self.assertEqual(4, diff_dict['core.NullDereference'])
