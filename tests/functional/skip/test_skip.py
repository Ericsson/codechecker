#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" skip function test.  """

import os
import logging
import unittest

from libtest.debug_printer import print_run_results
from libtest.thrift_client_to_db import get_all_run_results
from libtest.result_compare import find_all
from libtest import env


class TestSkip(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        # Get the test configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         "There should be only one run for this test.")
        self._runid = test_runs[0].runId

    def test_skip(self):
        """ There should be no results from the skipped file. """

        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)

        skipped_file = "file_to_be_skipped.cpp"

        test_proj_res = self._testproject_data[self._clang_to_test]['bugs']
        skipped = [x for x in test_proj_res if x['file'] == skipped_file]
        print("Analysis:")
        for res in run_results:
            print(res)

        print("Test config results:")
        for res in test_proj_res:
            print(res)

        print("Test config skipped results:")
        for res in skipped:
            print(res)

        self.assertEqual(len(run_results), len(test_proj_res) - len(skipped))

        missing_results = find_all(run_results, test_proj_res)

        print_run_results(run_results)

        print('Missing results:')
        for mr in missing_results:
            print(mr)

        if missing_results:
            for bug in missing_results:
                self.assertEqual(bug['file'], skipped_file)
        else:
            self.assertTrue(True,
                            "There should be missing results because"
                            "using skip")
