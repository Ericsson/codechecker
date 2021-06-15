#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Report exporting and importing tests
"""


import os
import unittest
import logging
import json
import tempfile

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentData, \
    ReviewStatus, CommentKind, RunFilter

from libtest import env
from libtest.thrift_client_to_db import get_all_run_results
import subprocess


def get_user_comments(comments):
    """
    Separate comments and returns a tuple of user comments and system.
    """
    user_comments = [c for c in comments
                     if c.kind == CommentKind.USER]

    return user_comments


class TestExport(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        codechecker_cfg = env.import_test_cfg(test_workspace)[
            'codechecker_cfg']
        self.server_url = env.parts_to_url(codechecker_cfg)

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
        self.test_runs = [run for run in runs if run.name in run_names]

    def test_export_import(self):
        """
        Test exporting and importing feature
        """
        run_filter = RunFilter()
        run_filter.names = [self.test_runs[0].name]
        logging.debug('Get all run results from the db for runid: ' +
                      str(self.test_runs[0].runId))

        run_results = get_all_run_results(
            self._cc_client, self.test_runs[0].runId)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug = run_results[0]

        # There are no comments available for the first bug
        comments = self._cc_client.getComments(bug.reportId)
        self.assertEqual(len(comments), 0)

        comment1 = CommentData(author='anybody', message='First msg')
        success = self._cc_client.addComment(bug.reportId, comment1)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Try to add another new comment for the first bug
        comment2 = CommentData(author='anybody', message='Second msg')
        success = self._cc_client.addComment(bug.reportId, comment2)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Change review status
        review_comment = 'This is really a bug'
        status = ReviewStatus.CONFIRMED
        success = self._cc_client.changeReviewStatus(
            bug.reportId, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        # Export the comments and reviews
        exported = self._cc_client.exportData(run_filter)
        exported_comments = exported.comments[bug.bugHash]
        exported_review = exported.reviewData[bug.bugHash]

        # Check if the comments are same
        user_comments = get_user_comments(exported_comments)
        self.assertEqual(user_comments[0].message, comment2.message)
        self.assertEqual(user_comments[1].message, comment1.message)

        # Check for the review status
        self.assertEqual(exported_review.status, status)
        self.assertEqual(exported_review.comment, review_comment)

        new_export_command = [self._codechecker_cmd, 'cmd', 'export',
                              '-n', self.test_runs[0].name,
                              '--url', str(self.server_url)]

        print(new_export_command)
        out_json = subprocess.check_output(
            new_export_command, encoding="utf-8", errors="ignore")
        resolved_results = json.loads(out_json)
        print(resolved_results)
        with tempfile.NamedTemporaryFile() as component_f:
            component_f.write(out_json.encode('utf-8'))
            component_f.flush()
            component_f.seek(0)

            self._cc_client.removeComment(user_comments[0].id)
            updated_message = "The new comment for testing"
            self._cc_client.updateComment(user_comments[1].id, updated_message)

            new_import_command = [self._codechecker_cmd, 'cmd', 'import',
                                  '-i', component_f.name,
                                  '--url', str(self.server_url)]
            print(new_import_command)
            subprocess.check_output(
                new_import_command, encoding="utf-8", errors="ignore")

            exported = self._cc_client.exportData(run_filter)
            new_comments = exported.comments[bug.bugHash]
            print(new_comments)

            # Check if the last and second last comments
            self.assertEqual(new_comments[-2].message, comment1.message)
            self.assertEqual(new_comments[-1].message, updated_message)
