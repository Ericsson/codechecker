# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the CodeChecker command line.
"""


import json
import os
import shutil
import subprocess
import sys
import uuid
import tempfile
import unittest

from libtest import codechecker
from libtest import env
from libtest import project
from codechecker_api_shared.ttypes import RequestFailed, Permission


def run_cmd(cmd, environ=None):
    print(cmd)
    proc = subprocess.Popen(
        cmd,
        env=environ,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="ignore")

    out, err = proc.communicate()
    print(out)
    return proc.returncode, out, err


class TestFilterPresetCmdLine(unittest.TestCase):
    """
    Simple tests to check CodeChecker filter-preset command line.
    """

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('cmdline')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_project = 'cpp'

        test_config = {}

        project_info = project.get_info(test_project)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(project.path(test_project), test_proj_path)

        project_info['project_path'] = test_proj_path

        test_config['test_project'] = project_info

        suppress_file = None

        skip_list_file = None

        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'suppress_file': suppress_file,
            'skip_list_file': skip_list_file,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'description': "Runs for command line test."
        }

        ret = project.clean(test_project)
        if ret:
            sys.exit(ret)

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'cmdline'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Generate a unique name for this test run.
        test_project_name_1 = project_info['name'] + '1_' + uuid.uuid4().hex

        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name_1,
                                          project.path(test_project))
        if ret:
            sys.exit(1)
        print("Analyzing the test project was successful.")

        test_project_name_2 = project_info['name'] + '2_' + uuid.uuid4().hex

        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name_2,
                                          project.path(test_project))
        if ret:
            sys.exit(1)
        print("Analyzing the test project was successful.")

        codechecker_cfg['run_names'] = [test_project_name_1,
                                        test_project_name_2]

        test_config['codechecker_cfg'] = codechecker_cfg

        env.export_test_cfg(TEST_WORKSPACE, test_config)

    def teardown_class(self):
        """Clean up after the test."""

        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, _):

        test_workspace = os.environ.get('TEST_WORKSPACE')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        self.codechecker_cfg = env.import_test_cfg(test_workspace)[
            'codechecker_cfg']
        self.server_url = env.parts_to_url(self.codechecker_cfg)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        self._test_config = env.import_test_cfg(test_workspace)

    def test_filter_preset_cmd_help(self):
        """
        Test the filter-preset -help command line.
        """

        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', '-h']
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertIn("usage: CodeChecker cmd filter-preset", out)
        self.assertIn("options:", out)
        self.assertIn("available actions:", out)
        self.assertIn("list", out)
        self.assertIn("new", out)
        self.assertIn("delete", out)

    def test_filter_preset_cmd_new(self):
        """
        Test the filter-preset new command line.
        """
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
               '--name', 'test_preset', '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertIn("Filter preset 'test_preset' created successfully.", out)

        # call for list function to check if the preset is listed
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'list',
               '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertIn("test_preset", out)

    def test_filter_preset_cmd_new_no_name(self):
        """
        Test the filter-preset new command line without providing a name.
        """
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new', '--name',
               '--url', str(self.server_url)]
        ret, _, err = run_cmd(cmd)

        self.assertEqual(ret, 1)
        self.assertIn("argument --name: expected one argument", err)

    def test_filter_preset_cmd_new_overwrite(self):
        """
        Test the filter-preset new command line with overwrite.
        """
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
               '--name', 'test_preset_overwrite', '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertIn("Filter preset 'test_preset_overwrite' created successfully.", out)

        # call for list function to check if the preset is listed
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'list',
               '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertIn("test_preset_overwrite", out)

        # create new preset with the same id but different name to check if it is overwritten
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
               '--name', 'test_preset_overwrite_2', '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

    def test_filter_preset_cmd_delete(self):
        """
        Test the filter-preset delete command line.
        """

        cmd1 = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
               '--name', 'test_preset_to_delete', '--url', str(self.server_url)]

        cmd2 = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
               '--name', 'test_preset_to_stay', '--url', str(self.server_url)]

        ret1, out1, _ = run_cmd(cmd1)
        ret2, out2, _ = run_cmd(cmd2)

        self.assertEqual(ret1, 0)
        self.assertIn("Filter preset 'test_preset_to_delete' created successfully.", out1)

        self.assertEqual(ret2, 0)
        self.assertIn("Filter preset 'test_preset_to_stay' created successfully.", out2)

        # delete the preset
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'delete',
               '--id', '1', '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertIn("test_preset_to_delete", out)
        self.assertIn("successfully deleted.", out)

        # check if is still present in list
        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'list',
               '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertNotIn("test_preset_to_delete", out)
        self.assertIn("test_preset_to_stay", out)

    def test_filter_preset_cmd_delete_non_existing(self):
        """
        Test the filter-preset delete command line with non existing id.
        """

        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'delete',
               '--id', '999', '--url', str(self.server_url)]

        ret, out, _ = run_cmd(cmd)
        self.assertEqual(ret, 1)
        self.assertIn("Filter preset with ID 999 does not exist!", out)

    def test_filter_preset_cmd_list(self):
        """
        Test the filter-preset list command line.
        """

        # add 4 presets to the server and 1 failed one without provided id
        cmd1 = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
                '--name', 'test_preset_1', '--url', str(self.server_url)]
        cmd2 = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
                '--name', 'test_preset_2', '--url', str(self.server_url)]
        cmd3 = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
                '--name', 'test_preset_3', '--url', str(self.server_url)]
        cmd4 = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
                '--name', 'test_preset_4', '--url', str(self.server_url)]
        cmd5 = [self._codechecker_cmd, 'cmd', 'filter-preset', 'new',
                '--name', 'test_preset_4', '--url', str(self.server_url)]

        run_cmd(cmd1)
        run_cmd(cmd2)
        run_cmd(cmd3)
        run_cmd(cmd4)

        ret5, _, _ = run_cmd(cmd5)
        self.assertEqual(ret5, 1)

        cmd = [self._codechecker_cmd, 'cmd', 'filter-preset', 'list',
               '--url', str(self.server_url)]
        ret, out, _ = run_cmd(cmd)

        self.assertEqual(ret, 0)
        self.assertIn("test_preset", out)
