#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
Test removing run results feature.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import sys
import unittest

from codeCheckerDBAccess_v6.ttypes import ReportFilter, RunFilter

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

        runs = self._cc_client.getRunData(None)

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
        runs = self._cc_client.getRunData(run_filter)
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
        self._cc_client.removeRun(run_id)

        # Check that we removed all results from the run.
        res = self._cc_client.getRunResultCount([run_id], None, None)
        self.assertEqual(res, 0)
