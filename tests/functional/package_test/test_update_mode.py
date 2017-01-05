#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import os
import unittest
import logging

import shared

from test_utils.thrift_client_to_db import CCViewerHelper


class UpdateMode(unittest.TestCase):

    def setUp(self):
        host = 'localhost'
        port = int(os.environ['CC_TEST_VIEWER_PORT'])
        uri = '/'
        self._testproject_data = json.loads(os.environ['CC_TEST_PROJECT_INFO'])
        self.assertIsNotNone(self._testproject_data)
        self._cc_client = CCViewerHelper(host, port, uri)

    # -----------------------------------------------------
    def test_get_update_run_res(self):
        """
        The test depends on a run which was configured for update mode.
        Compared to the original test analysis in this run
        the deadcode.Deadstores checker was disabled.
        """
        runs = self._cc_client.getRunData()
        self.assertIsNotNone(runs)
        self.assertNotEqual(len(runs), 0)
        self.assertGreaterEqual(len(runs), 2)

        update_run_name = "update_test"
        updated_run = None
        for run in runs:
            print(run.name)
            if run.name == update_run_name:
                updated_run = run
                break
        print('There should be a run with this name: ' + update_run_name)
        self.assertIsNotNone(updated_run)

        # get all the results from the test project config
        bugs = self._testproject_data['bugs']
        all_results = len(bugs)
        deadcode_results = [b for b in bugs
                            if b['checker'] == 'deadcode.DeadStores']

        deadcode_count = len(deadcode_results)

        update_res_count = None
        results = self._cc_client.getRunResults(updated_run.runId,
                                                500, 0, [], [])
        update_res_count = len(results)

        self.assertEqual(all_results - deadcode_count, update_res_count)
