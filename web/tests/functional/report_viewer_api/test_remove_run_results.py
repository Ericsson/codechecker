#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test removing run results feature.
"""


import os
import sys
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import Order, \
    ReportFilter, RunFilter, RunSortMode, RunSortType

from libtest import codechecker
from libtest import env
from libtest import project


class RemoveRunResults(unittest.TestCase):
    """ Tests for removing run results. """

    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(test_workspace)
        self._test_dir = os.path.join(test_workspace, 'test_files')

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        sort_mode = RunSortMode(RunSortType.DATE, Order.ASC)
        runs = self._cc_client.getRunData(None, None, 0, sort_mode)

        test_runs = [run for run in runs if run.name in run_names]

        self._runid = test_runs[0].runId

    def test_remove_run_results(self):
        """
        Test for removing run results and run.
        """
        # Run the anaysis again with different setup.
        test_project_path = self._testproject_data['project_path']
        ret = project.clean(test_project_path)
        if ret:
            sys.exit(ret)

        codechecker.check_and_store(self._codechecker_cfg,
                                    'remove_run_results',
                                    test_project_path)

        run_filter = RunFilter(names=['remove_run_results'], exactMatch=True)
        sort_mode = RunSortMode(RunSortType.DATE, Order.ASC)
        runs = self._cc_client.getRunData(run_filter, None, 0, sort_mode)
        self.assertEqual(len(runs), 1)

        run_id = runs[0].runId

        orig_results_count = \
            self._cc_client.getRunResultCount([run_id], None, None)
        self.assertNotEqual(orig_results_count, 0)

        checker_filter = ReportFilter(checkerName=["core.CallAndMessage"])
        res_count = self._cc_client.getRunResultCount([run_id],
                                                      checker_filter,
                                                      None)
        self.assertNotEqual(res_count, 0)

        self._cc_client.removeRunReports([run_id],
                                         checker_filter,
                                         None)

        res_count = self._cc_client.getRunResultCount([run_id],
                                                      checker_filter,
                                                      None)
        self.assertEqual(res_count, 0)

        # Remove the run.
        self._cc_client.removeRun(run_id, None)

        # Check that we removed all results from the run.
        res = self._cc_client.getRunResultCount([run_id], None, None)
        self.assertEqual(res, 0)
