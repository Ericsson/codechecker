#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test review status functionality."""


import datetime
import logging
import os
import time
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentKind, \
    ReviewStatus, RunFilter

from libtest import env, codechecker, plist_test
from libtest.thrift_client_to_db import get_all_run_results


class TestReviewStatus(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(self.test_workspace)
        # get the current run data
        run_filter = RunFilter(names=run_names, exactMatch=True)

        runs = self._cc_client.getRunData(run_filter, None, 0, None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test, '
                         'with the given name configured at the test init.')
        self._runid = test_runs[0].runId

    def __get_system_comments(self, report_hash):
        """ Get system comments for the given report hash. """
        return [c for c in self._cc_client.getComments(report_hash)
                if c.kind == CommentKind.SYSTEM]

    def test_multiple_change_review_status(self):
        """
        Test changing review status of the same bug.
        """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug = run_results[0]

        # There are no system comments for this bug.
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 0)

        # Change review status to confirmed bug.
        review_comment = 'This is really a bug'
        status = ReviewStatus.CONFIRMED
        success = self._cc_client.changeReviewStatus(
            bug.reportId, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, review_comment)
        self.assertEqual(report.reviewData.status, status)

        # There is one system comment for this bug.
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 1)

        # Try to update the review status again with the same data and check
        # that no new system comment entry will be created.
        success = self._cc_client.changeReviewStatus(
            bug.reportId, status, review_comment)
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 1)

        # Test that updating only the review status message a new system
        # comment will be created.
        success = self._cc_client.changeReviewStatus(
            bug.reportId, status, "test system comment change")
        self.assertTrue(success)
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 2)

        # Try to change review status back to unreviewed.
        status = ReviewStatus.UNREVIEWED
        success = self._cc_client.changeReviewStatus(
            bug.reportId,
            status,
            None)

        self.assertTrue(success)
        logging.debug("Bug review status changed successfully")

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, '')
        self.assertEqual(report.reviewData.status, status)

        # Change review status to false positive.
        review_comment = 'This is not a bug'
        status = ReviewStatus.FALSE_POSITIVE
        success = self._cc_client.changeReviewStatus(
            bug.reportId, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, review_comment)
        self.assertEqual(report.reviewData.status, status)

        # Change review status to intentional.
        review_comment = ''
        status = ReviewStatus.INTENTIONAL
        success = self._cc_client.changeReviewStatus(
            bug.reportId, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, review_comment)
        self.assertEqual(report.reviewData.status, status)

    def test_review_status_update_from_source_trim(self):
        """
        Test if the review status comments changes in the source code
        are updated at the server when trim path is used.

        The report is store twice and between the storage the
        review status as a source code comment is modified.
        The test checks is after the source code modification
        and storage the review status is updated correctly at
        the server too.
        """
        test_project_path = os.path.join(self.test_workspace,
                                         'review_status_files')
        test_project_name = 'review_status_update_proj'

        plist_file = os.path.join(test_project_path, 'divide_zero.plist')
        source_file = os.path.join(test_project_path, 'divide_zero.cpp')
        plist_test.prefix_file_path(plist_file, test_project_path)

        codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        codechecker_cfg['reportdir'] = test_project_path

        codechecker.store(codechecker_cfg, test_project_name)

        codechecker_cfg['trim_path_prefix'] = test_project_path

        # Run data for the run created by this test case.
        run_filter = RunFilter(names=[test_project_name], exactMatch=True)

        runs = self._cc_client.getRunData(run_filter, None, 0, None)
        run = runs[0]
        runid = run.runId
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        reports = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(reports)
        self.assertNotEqual(len(reports), 0)
        self.assertEqual(len(reports), 2)

        for report in reports:
            print(report)
            self.assertEqual(report.reviewData.status,
                             ReviewStatus.INTENTIONAL)

        # Modify review comments from intentional to confirmed for the
        # second store.
        with open(source_file, 'r+', encoding='utf-8', errors='ignore') as sf:
            content = sf.read()
            new_content = content.replace("codechecker_intentional",
                                          "codechecker_confirmed")
            sf.truncate(0)
            sf.write(new_content)

        # modify review comments and store the reports again
        with open(source_file, encoding='utf-8', errors='ignore') as sf:
            content = sf.read()

        # Update the plist file modification date to be newer than
        # the source file so it can be stored, because there was no
        # actual analysis.
        date = datetime.datetime.now() + datetime.timedelta(minutes=5)
        mod_time = time.mktime(date.timetuple())
        os.utime(plist_file, (mod_time, mod_time))

        codechecker.store(codechecker_cfg, test_project_name)

        # Check if all the review statuses were updated to the new at the
        # server.
        reports = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(reports)
        self.assertNotEqual(len(reports), 0)
        self.assertEqual(len(reports), 2)
        for report in reports:
            self.assertEqual(report.reviewData.status, ReviewStatus.CONFIRMED)
