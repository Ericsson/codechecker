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
import shutil
import unittest
import logging
import json
import sys
import uuid
import tempfile

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentData, \
    ReviewStatus, CommentKind, RunFilter

from libtest import codechecker
from libtest import env
from libtest import project
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

    def setup_class(self):
        """Setup the environment for testing export and import."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('export_import')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        test_project = 'cpp'

        project_info = project.get_info(test_project)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(project.path(test_project), test_proj_path)

        project_info['project_path'] = test_proj_path

        # Generate a unique name for this test run.
        test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

        test_config['test_project'] = project_info

        # Suppress file should be set here if needed by the tests.
        suppress_file = None

        # Skip list file should be set here if needed by the tests.
        skip_list_file = None

        # Get an environment which should be used by the tests.
        test_env = env.test_env(TEST_WORKSPACE)

        # Create a basic CodeChecker config for the tests, this should
        # be imported by the tests and they should only depend on these
        # configuration options.
        codechecker_cfg = {
            'suppress_file': suppress_file,
            'skip_list_file': skip_list_file,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': []
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'export_import'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Clean the test project, if needed by the tests.
        ret = project.clean(test_project)
        if ret:
            sys.exit(ret)

        # Check the test project, if needed by the tests.
        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name,
                                          project.path(test_project))
        if ret:
            sys.exit(1)
        print("Analyzing the test project was successful.")

        # Save the run names in the configuration.
        codechecker_cfg['run_names'] = [test_project_name]

        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
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

        comment1 = CommentData(author='anybody', message='First msg <img />')
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
