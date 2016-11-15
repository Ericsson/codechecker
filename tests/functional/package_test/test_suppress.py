# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import logging
import os
import unittest

from codeCheckerDBAccess.ttypes import ReportFilter

from test_utils.debug_printer import print_run_results
from test_utils.thrift_client_to_db import CCViewerHelper
from test_utils.thrift_client_to_db import get_all_run_results


class Suppress(unittest.TestCase):
    """
    Test suppress functionality
    """

    _ccClient = None

    # selected runid for running the tests
    _runid = None

    def _select_one_runid(self):
        """
        Select one run id for the test.
        """
        runs = self._cc_client.getRunData()
        self.assertIsNotNone(runs)
        self.assertNotEqual(len(runs), 0)
        idx = 0
        return runs[idx].runId

    def setUp(self):
        host = 'localhost'
        port = int(os.environ['CC_TEST_VIEWER_PORT'])
        uri = '/'
        self._testproject_data = json.loads(os.environ['CC_TEST_PROJECT_INFO'])
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = CCViewerHelper(host, port, uri)
        self._runid = self._select_one_runid()

    def test_double_suppress(self):
        """
        Suppressing the same bug for the second time should be successfull.
        The second suppress should not overwrite the
        already stored suppress comment.
        """

        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        suppress_comment = r'First suppress msg'
        bug = run_results[0]
        success = self._cc_client.suppressBug([runid],
                                              bug.reportId,
                                              suppress_comment)
        self.assertTrue(success)
        logging.debug('Bug suppressed successfully')

        # try to suppress the same bug again
        second_suppress_msg = r'Second suppress msg'
        success = self._cc_client.suppressBug([runid],
                                              bug.reportId,
                                              second_suppress_msg)
        self.assertTrue(success)
        logging.debug('Same bug suppressed successfully for the second time')

        simple_filters = [ReportFilter(suppressed=True)]
        run_results_suppressed = get_all_run_results(self._cc_client,
                                                     runid,
                                                     filters=simple_filters)

        self.assertIsNotNone(run_results_suppressed)
        self.assertEqual(len(run_results_suppressed), 1)

        bug_to_suppress = bug
        bug_to_suppress.suppressed = True
        bug_to_suppress.suppressComment = suppress_comment

        # The only one suppressed bug should be returned.
        self.assertEqual(bug_to_suppress, run_results_suppressed[0])

        success = self._cc_client.unSuppressBug([runid],
                                                bug_to_suppress.reportId)
        self.assertTrue(success)
        logging.debug('Bug unsuppressed successfully')

        simple_filters = [ReportFilter(suppressed=False)]
        run_results_unsuppressed = get_all_run_results(self._cc_client,
                                                       runid,
                                                       filters=simple_filters)

        self.assertIsNotNone(run_results_unsuppressed)
        self.assertEqual(len(run_results), len(run_results_unsuppressed))
