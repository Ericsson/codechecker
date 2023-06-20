#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Report commenting tests.
"""

import html
import logging
import os
import shutil
import sys
import uuid

import unittest

from codechecker_api_shared.ttypes import RequestFailed
from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentData, \
    CommentKind

from libtest import codechecker
from libtest import env
from libtest import project
from libtest.thrift_client_to_db import get_all_run_results


def separate_comments(comments):
    """
    Separate comments and returns a tuple of user comments and system.
    """
    user_comments = [c for c in comments
                     if c.kind == CommentKind.USER]

    system_comments = [c for c in comments
                       if c.kind == CommentKind.SYSTEM]

    return user_comments, system_comments


class TestComment(unittest.TestCase):

    _ccClient = None

    def setup_class(self):
        """Setup the environment for the tests. """

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('comment')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_project = 'cpp'

        test_project_path = project.path(test_project)

        test_config = {}

        project_info = project.get_info(test_project)

        test_config['test_project'] = project_info

        suppress_file = None

        skip_list_file = None

        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'suppress_file': suppress_file,
            'skip_list_file': skip_list_file,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
            'checkers': ['-d', 'core.CallAndMessage',
                         '-e', 'core.StackAddressEscape'],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server(auth_required=True)
        server_access['viewer_product'] = 'comment'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Check the test project for the first time.
        test_project_names = []
        test_project_name = project_info['name'] + '_' + uuid.uuid4().hex
        test_project_names.append(test_project_name)

        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name,
                                          test_project_path)
        if ret:
            sys.exit(1)
        print("Analyzing test project was successful.")

        # Check the test project again.
        test_project_name = project_info['name'] + '_' + uuid.uuid4().hex
        test_project_names.append(test_project_name)

        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name,
                                          test_project_path)
        if ret:
            sys.exit(1)
        print("Analyzing test project was succcessful.")

        codechecker_cfg['run_names'] = test_project_names
        test_config['codechecker_cfg'] = codechecker_cfg
        env.export_test_cfg(TEST_WORKSPACE, test_config)

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, method):
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

        runs = self._cc_client.getRunData(None, None, 0, None)

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
        first_msg = 'First msg <img />'
        comment1 = CommentData(author='anybody', message=first_msg)
        success = self._cc_client.addComment(bug.reportId, comment1)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Try to add another new comment for the first bug
        comment2 = CommentData(author='anybody', message='Second msg')
        success = self._cc_client.addComment(bug.reportId, comment2)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        # Try to add another new comment with empty message.
        with self.assertRaises(RequestFailed):
            self._cc_client.addComment(bug.reportId,
                                       CommentData(author='anybody'))

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

        self.assertIn(html.escape(first_msg), comments[0].message)

        num_comment = self._cc_client.getCommentCount(bug.reportId)
        self.assertEqual(num_comment, 1)

        # Edit the message of the first remaining comment
        new_msg = "New msg'\"` <img />"
        new_msg_escaped = html.escape(new_msg)
        success = self._cc_client.updateComment(comments[0].id, new_msg)
        self.assertTrue(success)
        logging.debug('Comment edited successfully')

        # Update comment with empty message.
        with self.assertRaises(RequestFailed):
            self._cc_client.updateComment(comments[0].id,
                                          '       ')

        john_msg = 'John cannot edit'
        with self.assertRaises(RequestFailed):
            self._cc_client_john.updateComment(comments[0].id, john_msg)
            logging.debug('Comment was edited by john')

        comments = self._cc_client.getComments(bug.reportId)
        user_comments, system_comments = separate_comments(comments)

        self.assertEqual(len(user_comments), 1)
        self.assertEqual(user_comments[0].message, new_msg_escaped)
        self.assertEqual(len(system_comments), 1)
        self.assertIn(new_msg_escaped, system_comments[0].message)

        # Test user and system comments fetched
        details = self._cc_client.getReportDetails(bug.reportId)
        user_c, system_c = separate_comments(details.comments)

        self.assertEqual(len(user_c), len(user_comments))
        self.assertEqual(user_c[0].message, user_comments[0].message)

        self.assertEqual(len(system_c), len(system_comments))
        self.assertEqual(system_c[0].message, system_comments[0].message)

        # Remove the last comment for the first bug
        success = self._cc_client.removeComment(user_comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        comments = self._cc_client.getComments(bug.reportId)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].kind, CommentKind.SYSTEM)

        num_comment = self._cc_client.getCommentCount(bug.reportId)
        self.assertEqual(num_comment, 1)

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

        bug_new = next(x for x in run_results_new
                       if x.bugHash == bug_base.bugHash)

        # Both bug have the same bug hash.
        self.assertEqual(bug_base.bugHash, bug_new.bugHash)

        # There are no comments available for the bug.
        comments = self._cc_client.getComments(bug_base.reportId)
        user_comments, _ = separate_comments(comments)
        self.assertEqual(len(user_comments), 0)

        comments = self._cc_client.getComments(bug_new.reportId)
        user_comments, _ = separate_comments(comments)
        self.assertEqual(len(user_comments), 0)

        # Try to add a new comment for the first bug
        comment = CommentData(author='Anonymous', message='First msg')
        success = self._cc_client.addComment(bug_base.reportId, comment)
        self.assertTrue(success)
        logging.debug('Bug commented successfully')

        comments = self._cc_client.getComments(bug_base.reportId)
        user_comments, _ = separate_comments(comments)
        self.assertEqual(len(user_comments), 1)

        comments = self._cc_client.getComments(bug_new.reportId)
        user_comments, _ = separate_comments(comments)
        self.assertEqual(len(user_comments), 1)

        # Remove the comment for the bug.
        success = self._cc_client.removeComment(comments[0].id)
        self.assertTrue(success)
        logging.debug('Comment removed successfully')

        comments = self._cc_client.getComments(bug_base.reportId)
        user_comments, _ = separate_comments(comments)
        self.assertEqual(len(user_comments), 0)

        comments = self._cc_client.getComments(bug_new.reportId)
        user_comments, _ = separate_comments(comments)
        self.assertEqual(len(user_comments), 0)
