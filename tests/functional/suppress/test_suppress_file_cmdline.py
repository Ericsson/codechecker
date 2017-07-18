#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import unittest

from libtest import env


class SuppressSetInCmdLine(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]

        # There should be only one run for this test.
        self.assertEqual(len(test_runs), 1)
        self._runid = test_runs[0].runId

    def test_suppress_file_set_in_cmd(self):
        """
        Server is started with a suppress file check if the api
        returns a non empty string tempfile is used for suppress
        file so name will change for each run.
        """
        self.assertNotEquals(self._cc_client.getSuppressFile(), '')
