#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" $TEST_NAME$ function test.

WARNING!!!
This is a generated test skeleton remove the parts not required by the tests.
WARNING!!!

"""


import os
import unittest

from libtest import env


class TestSkeleton(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        """
        WARNING!!!
        This is an example how to get the configurations needed by the tests.
        WARNING!!!
        """

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        test_cfg = env.import_test_cfg(test_workspace)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        runs = self._cc_client.getRunData(None, None, 0, None)
        test_runs = [run for run in runs if run.name in run_names]

    def test_skel(self):
        """
        Test some feature.
        """
        pass
