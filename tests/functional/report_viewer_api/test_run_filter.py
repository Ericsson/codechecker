#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import unittest

from libtest import env


class TestRunFilter(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        self._run_names = env.get_run_names(test_workspace)

    def __get_runs(self, run_name_filter=None):
        """ Helper function to get all run names which belong to this test"""
        runs = self._cc_client.getRunData(run_name_filter)

        return [run for run in runs if run.name in self._run_names]

    def test_filter_run_names(self):
        # Filter all runs.
        test_runs = self.__get_runs()

        # Filter runs which name starts with `test_files_`.
        test_runs = self.__get_runs('test_files_')
        self.assertEqual(len(test_runs), 2,
                         "There should be two runs for this test.")

        # Run name filter is case insensitive.
        test_runs = self.__get_runs('Test_Files_')
        self.assertEqual(len(test_runs), 2,
                         "There should be two runs for this test.")

        # Filter runs which name contains `files`.
        test_runs = self.__get_runs('files_')
        self.assertEqual(len(test_runs), 2,
                         "There should be two runs for this test.")

        # Filter non existing run.
        test_runs = self.__get_runs('non_existing_run_name')
        self.assertEqual(len(test_runs), 0,
                         "There should be no run for this test.")
