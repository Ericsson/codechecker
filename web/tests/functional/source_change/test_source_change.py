#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Tests for source file changes
"""


import os
import time
import shutil
import sys
import unittest
import uuid

from libtest import codechecker
from libtest import env
from libtest import project


def touch(fname, times=None):
    """
    Modify the update and last modification times for a file.
    """
    with open(fname, 'a', encoding="utf-8", errors="ignore"):
        os.utime(fname, times)


class TestSkeleton(unittest.TestCase):

    _ccClient = None

    def setup_class(self):
        """Setup the environment for testing source_change."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('source_change')

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

        # Get an environment which should be used by the tests.
        test_env = env.test_env(TEST_WORKSPACE)

        # Create a basic CodeChecker config for the tests, this should
        # be imported by the tests and they should only depend on these
        # configuration options.
        codechecker_cfg = {
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
            'checkers': [],
            'analyzers': ['clangsa']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'source_change'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Clean the test project, if needed by the tests.
        ret = project.clean(test_project)
        if ret:
            sys.exit(ret)

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
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        self.env = env.codechecker_env()

    def test_parse(self):
        """
        Test if there are skip messages in the output of the parse command if
        the source files did change between the analysis and the parse.
        """

        test_proj_path = self._testproject_data['project_path']

        test_proj_files = os.listdir(test_proj_path)
        print(test_proj_files)

        null_deref_file = os.path.join(test_proj_path, 'null_dereference.cpp')

        codechecker.log_and_analyze(self._codechecker_cfg,
                                    test_proj_path)

        ret, out, _ = codechecker.parse(self._codechecker_cfg)
        self.assertEqual(ret, 2)

        # Need to wait a little before updating the last modification time.
        # If we do not wait, not enough time will be past
        # between the analysis and the parse in the test.
        time.sleep(2)
        touch(null_deref_file)

        ret, out, _ = codechecker.parse(self._codechecker_cfg)
        self.assertEqual(ret, 2)

        msg = 'changed or missing since the latest analysis'
        self.assertTrue(msg in out,
                        '"' + msg + '" was not found in the parse output')

    def test_store(self):
        """
        Store should fail if the source files were modified since the
        last analysis.
        """

        test_proj = os.path.join(self.test_workspace, 'test_proj')

        ret = codechecker.check_and_store(self._codechecker_cfg,
                                          'test_proj',
                                          test_proj)

        self.assertEqual(ret, 0)

        ret = codechecker.store(self._codechecker_cfg, 'test_proj')
        self.assertEqual(ret, 0)

        test_proj_path = self._testproject_data['project_path']

        test_proj_files = os.listdir(test_proj_path)
        print(test_proj_files)

        null_deref_file = os.path.join(test_proj_path, 'null_dereference.cpp')

        touch(null_deref_file)

        ret = codechecker.store(self._codechecker_cfg, 'test_proj')
        self.assertEqual(ret, 1)

    def test_store_config_file_mod(self):
        """Storage should be successful if a non report related file changed.

        Checking the modification time stamps should be done only for
        the source files mentioned in the report plist files.
        Modifying any non report related file should not prevent the storage
        of the reports.
        """
        test_proj = os.path.join(self.test_workspace, 'test_proj')

        ret = codechecker.log(self._codechecker_cfg, test_proj,
                              clean_project=True)
        self.assertEqual(ret, 0)

        ret = codechecker.analyze(self._codechecker_cfg, test_proj)
        self.assertEqual(ret, 0)

        test_proj_path = self._testproject_data['project_path']

        # touch one file so it will be analyzed again
        touch(os.path.join(test_proj_path, 'null_dereference.cpp'))

        ret = codechecker.log(self._codechecker_cfg, test_proj)
        self.assertEqual(ret, 0)

        ret = codechecker.analyze(self._codechecker_cfg,
                                  test_proj)
        self.assertEqual(ret, 0)

        touch(os.path.join(self._codechecker_cfg['reportdir'],
                           'compile_cmd.json'))

        ret = codechecker.store(self._codechecker_cfg, 'test_proj')
        self.assertEqual(ret, 0)
