# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import logging
import os
import unittest

from codeCheckerDBAccess.ttypes import ReportFilter

from libtest.debug_printer import print_run_results
from libtest.thrift_client_to_db import CCViewerHelper
from libtest.thrift_client_to_db import get_all_run_results
from libtest import env

"""
Test suppression functionality.
"""


class TestSuppress(unittest.TestCase):
    """
    Test suppress functionality
    """

    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        test_cfg = env.import_test_cfg(test_workspace)

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        runs = self._cc_client.getRunData()

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test.')
        self._runid = test_runs[0].runId

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

        # Try to suppress the same bug again.
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

    def test_get_run_results_checker_msg_filter_suppressed(self):

        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        simple_filters = [ReportFilter(suppressed=False)]
        run_results = self._cc_client.getRunResults(runid, 50, 0, [],
                                                    simple_filters)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        suppress_msg = r'My beautiful Unicode comment.'
        bug = run_results[0]
        success = self._cc_client.suppressBug([runid],
                                              bug.reportId,
                                              suppress_msg)
        self.assertTrue(success)
        logging.debug('Bug suppressed successfully')

        simple_filters = [ReportFilter(suppressed=True)]
        run_results = self._cc_client.getRunResults(runid, 50, 0, [],
                                                    simple_filters)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        filtered_run_results = filter(
            lambda result:
            (result.reportId == bug.reportId) and result.suppressed,
            run_results)
        self.assertEqual(len(filtered_run_results), 1)
        suppressed_bug = filtered_run_results[0]
        self.assertEqual(suppressed_bug.suppressComment, suppress_msg)

        success = self._cc_client.unSuppressBug([runid],
                                                suppressed_bug.reportId)
        self.assertTrue(success)
        logging.debug('Bug unsuppressed successfully')

        simple_filters = [ReportFilter(suppressed=False)]
        run_results = self._cc_client.getRunResults(runid, 50, 0, [],
                                                    simple_filters)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        filtered_run_results = filter(
            lambda result:
            (result.reportId == bug.reportId) and not result.suppressed,
            run_results)
        self.assertEqual(len(filtered_run_results), 1)

        logging.debug('Done.\n')
