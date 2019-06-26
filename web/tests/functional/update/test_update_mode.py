#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test update mode where multiple analysis results stored in the same run.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import sys
import unittest

from libtest import env
from libtest import project
from libtest import codechecker
from libtest.debug_printer import print_run_results
from libtest.thrift_client_to_db import get_all_run_results


class TestUpdate(unittest.TestCase):

    def setUp(self):
        self._test_workspace = os.environ.get('TEST_WORKSPACE')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test
        run_names = env.get_run_names(self._test_workspace)

        runs = self._cc_client.getRunData(None, None, 0)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test.')
        self._runid = test_runs[0].runId
        self._run_name = test_runs[0].name

    def test_disable_checker(self):
        """
        The test depends on a run which was configured for update mode.
        Compared to the original test analysis in this run
        the deadcode.Deadstores checker was disabled.
        """

        run_results = get_all_run_results(self._cc_client, self._runid)

        print_run_results(run_results)

        # Run the anaysis again with different setup.
        test_project_path = self._testproject_data['project_path']
        ret = project.clean(test_project_path)
        if ret:
            sys.exit(ret)

        initial_codechecker_cfg = env.import_test_cfg(
            self._test_workspace)['codechecker_cfg']

        # Disable some checkers for the analysis.
        deadcode = 'deadcode.DeadStores'
        initial_codechecker_cfg['checkers'] = ['-d', deadcode]

        initial_test_project_name = self._run_name

        ret = codechecker.check_and_store(initial_codechecker_cfg,
                                          initial_test_project_name,
                                          test_project_path)
        if ret:
            sys.exit(1)

        # Get the results to compare.
        updated_results = get_all_run_results(self._cc_client, self._runid)

        all_bugs = self._testproject_data[self._clang_to_test]['bugs']
        deadcode_bugs = \
            [bug['hash'] for bug in all_bugs if bug['checker'] == deadcode]

        self.assertEquals(len(updated_results), len(all_bugs))
        self.assertTrue(all(map(
            lambda b: b.detectionStatus == 'unresolved',
            filter(lambda x: x in deadcode_bugs, updated_results))))
