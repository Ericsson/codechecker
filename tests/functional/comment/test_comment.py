#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import logging
import os
import unittest

from codeCheckerDBAccess.ttypes import CommentData

from libtest.thrift_client_to_db import get_all_run_results
from libtest import env


class TestComment(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        self._test_workspace = os.environ.get('TEST_WORKSPACE')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test
        run_names = env.get_run_names(self._test_workspace)

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test.')
        self._runid = test_runs[0].runId
        self._run_name = test_runs[0].name

    def test_comment(self):
        """
        Test commenting of multiple bugs.
        """

        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug = run_results[0]

        # There are no comments available for the first bug
        comments = self._cc_client.getComments(bug.bugHash)
        self.assertEqual(len(comments), 0)

        num_comment = self._cc_client.getCommentCount(bug.bugHash)
        self.assertEqual(num_comment, 0)

        # Try to add a new comment for the first bug
        comment1 = CommentData(author='Anonymous', message='First msg')
        success = self._cc_client.addComment(bug.bugHash, comment1)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Try to add another new comment for the first bug
        comment2 = CommentData(author='Anonymous', message='Second msg')
        success = self._cc_client.addComment(bug.bugHash, comment2)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Add new comment for the second bug
        bug2 = run_results[1]
        comment3 = CommentData(author='Anonymous', message='Third msg')
        success = self._cc_client.addComment(bug2.bugHash, comment3)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # There are two comments available for the first bug
        comments = self._cc_client.getComments(bug.bugHash)
        self.assertEqual(len(comments), 2)

        num_comment = self._cc_client.getCommentCount(bug.bugHash)
        self.assertEqual(num_comment, 2)

        # Check the order of comments (first comment is the earliest)
        self.assertGreater(comments[0].createdAt, comments[1].createdAt)

        # Remove the first comment
        success = self._cc_client.removeComment(comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        comments = self._cc_client.getComments(bug.bugHash)
        self.assertEqual(len(comments), 1)

        num_comment = self._cc_client.getCommentCount(bug.bugHash)
        self.assertEqual(num_comment, 1)

        # Edit the message of the first remaining comment
        new_msg = 'New msg'
        success = self._cc_client.updateComment(comments[0].id, new_msg)
        self.assertTrue(success)
        logging.debug('Comment edited successfully')

        comments = self._cc_client.getComments(bug.bugHash)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].message, new_msg)

        # Remove the last comment for the first bug
        success = self._cc_client.removeComment(comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        comments = self._cc_client.getComments(bug.bugHash)
        self.assertEqual(len(comments), 0)

        num_comment = self._cc_client.getCommentCount(bug.bugHash)
        self.assertEqual(num_comment, 0)
