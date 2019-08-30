#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Report commenting tests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging
import os
import unittest

from codechecker_api_shared.ttypes import RequestFailed
from codeCheckerDBAccess_v6.ttypes import CommentData

from libtest import env
from libtest.thrift_client_to_db import get_all_run_results


class TestComment(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        self._test_workspace = os.environ.get('TEST_WORKSPACE')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')

        sessionToken_cc = auth_client.performLogin("Username:Password",
                                                   "cc:test")
        sessionToken_john = auth_client.performLogin("Username:Password",
                                                     "john:doe")
        self._cc_client =\
            env.setup_viewer_client(
                self._test_workspace,
                session_token=sessionToken_cc)

        self._cc_client_john =\
            env.setup_viewer_client(
                self._test_workspace,
                session_token=sessionToken_john)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test
        run_names = env.get_run_names(self._test_workspace)

        runs = self._cc_client.getRunData(None, None, 0)

        self._test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(self._test_runs), 2,
                         'There should be two runs for this test.')

    def test_comment(self):
        """
        Test commenting of multiple bugs.
        """

        runid = self._test_runs[0].runId
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug = run_results[0]

        # There are no comments available for the first bug
        comments = self._cc_client.getComments(bug.reportId)
        self.assertEqual(len(comments), 0)

        num_comment = self._cc_client.getCommentCount(bug.reportId)
        self.assertEqual(num_comment, 0)

        # Try to add a new comment for the first bug
        comment1 = CommentData(author='anybody', message='First msg')
        success = self._cc_client.addComment(bug.reportId, comment1)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Try to add another new comment for the first bug
        comment2 = CommentData(author='anybody', message='Second msg')
        success = self._cc_client.addComment(bug.reportId, comment2)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Add new comment for a second bug with a different hash!
        bug2 = None
        for b in run_results:
            if b.bugHash != bug.bugHash:
                bug2 = b

        comment3 = CommentData(author='anybody', message='Third msg')
        success = self._cc_client.addComment(bug2.reportId, comment3)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # There are two comments available for the first bug
        comments = self._cc_client.getComments(bug.reportId)
        self.assertEqual(len(comments), 2)
        for c in comments:
            self.assertEqual(c.author, 'cc')

        num_comment = self._cc_client.getCommentCount(bug.reportId)
        self.assertEqual(num_comment, 2)

        # Check the order of comments (first comment is the earliest)
        self.assertGreater(comments[0].createdAt, comments[1].createdAt)

        # Remove the first comment
        print("removing comment:"+str(comments[0].id))
        success = self._cc_client.removeComment(comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        # Remove the second comment as john should be unsuccessful
        print("removing comment:"+str(comments[1].id))
        with self.assertRaises(RequestFailed):
            self._cc_client_john.removeComment(comments[1].id)
            logging.debug('Comment was removed by another user')

        comments = self._cc_client.getComments(bug.reportId)
        self.assertEqual(len(comments), 1)

        num_comment = self._cc_client.getCommentCount(bug.reportId)
        self.assertEqual(num_comment, 1)

        # Edit the message of the first remaining comment
        new_msg = 'New msg'
        success = self._cc_client.updateComment(comments[0].id, new_msg)
        self.assertTrue(success)
        logging.debug('Comment edited successfully')

        john_msg = 'John cannot edit'
        with self.assertRaises(RequestFailed):
            self._cc_client_john.updateComment(comments[0].id, john_msg)
            logging.debug('Comment was edited by john')

        comments = self._cc_client.getComments(bug.reportId)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].message, new_msg)

        # Remove the last comment for the first bug
        success = self._cc_client.removeComment(comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        comments = self._cc_client.getComments(bug.reportId)
        self.assertEqual(len(comments), 0)

        num_comment = self._cc_client.getCommentCount(bug.reportId)
        self.assertEqual(num_comment, 0)

        # Remove the last comment for the second bug.
        comments = self._cc_client.getComments(bug2.reportId)
        self.assertEqual(len(comments), 1)

        success = self._cc_client.removeComment(comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        comments = self._cc_client.getComments(bug2.reportId)
        self.assertEqual(len(comments), 0)

        num_comment = self._cc_client.getCommentCount(bug2.reportId)
        self.assertEqual(num_comment, 0)

    def test_same_bug_hash(self):
        """
        Test that different report ID's referring the same bug hash can
        query each other's comments.
        """

        # Get run results for the first run.
        runid_base = self._test_runs[0].runId
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid_base))

        run_results_base = get_all_run_results(self._cc_client, runid_base)
        self.assertIsNotNone(run_results_base)
        self.assertNotEqual(len(run_results_base), 0)

        bug_base = run_results_base[0]

        # Get run results for the second run.
        runid_new = self._test_runs[1].runId
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid_new))

        run_results_new = get_all_run_results(self._cc_client, runid_new)
        self.assertIsNotNone(run_results_new)
        self.assertNotEqual(len(run_results_new), 0)

        bug_new = run_results_new[0]

        # Both bug have the same bug hash.
        self.assertEqual(bug_base.bugHash, bug_new.bugHash)

        # There are no comments available for the bug.
        comments = self._cc_client.getComments(bug_base.reportId)
        self.assertEqual(len(comments), 0)

        comments = self._cc_client.getComments(bug_new.reportId)
        self.assertEqual(len(comments), 0)

        # Try to add a new comment for the first bug
        comment = CommentData(author='Anonymous', message='First msg')
        success = self._cc_client.addComment(bug_base.reportId, comment)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        comments = self._cc_client.getComments(bug_base.reportId)
        self.assertEqual(len(comments), 1)

        comments = self._cc_client.getComments(bug_new.reportId)
        self.assertEqual(len(comments), 1)

        # Remove the comment for the bug.
        success = self._cc_client.removeComment(comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        comments = self._cc_client.getComments(bug_base.reportId)
        self.assertEqual(len(comments), 0)

        comments = self._cc_client.getComments(bug_new.reportId)
        self.assertEqual(len(comments), 0)
