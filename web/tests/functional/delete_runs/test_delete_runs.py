#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Testing deletion of multiple runs.
"""


import json
import os
import shutil
import sys
import time
import subprocess
import unittest

from datetime import datetime

from libtest import codechecker
from libtest import env
from libtest import project


def run_cmd(cmd, env):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        env=env,
        encoding="utf-8",
        errors="ignore")
    out, _ = proc.communicate()
    return out, proc.returncode


class TestCmdLineDeletion(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing delete_runs."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('delete_runs')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        test_project = 'simple'

        project_info = project.get_info(test_project)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(project.path(test_project), test_proj_path)

        project_info['project_path'] = test_proj_path

        # Generate a unique name for this test run.
        test_project_name = project_info['name']

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
            'checkers': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'delete_runs'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        for i in range(0, 5):
            # Clean the test project, if needed by the tests.
            ret = project.clean(test_project)
            if ret:
                sys.exit(ret)

            # Check the test project, if needed by the tests.
            ret = codechecker.check_and_store(codechecker_cfg,
                                              test_project_name + '_' + str(i),
                                              test_proj_path)
            if ret:
                sys.exit(1)

            print("Analyzing the test project was successful {}."
                  .format(str(i)))

            # If the check process is very fast, datetime of multiple runs can
            # be almost the same different in microseconds. Test cases of
            # delete runs can be failed for this reason because we didn't
            # process microseconds in command line arguments.
            time.sleep(1)

        # Save the run names in the configuration.
        codechecker_cfg['run_names'] \
            = [test_project_name + '_' + str(i) for i in range(0, 5)]

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

        self._test_config = env.import_test_cfg(test_workspace)

    def test_multiple_deletion(self):
        """
        Test deletion of multiple runs.
        In the beginning five runs are placed in the database. This test checks
        if more runs can be deleted at once by --all-after-run and
        --all-before-time command line functions. Deleting a run by name should
        also work.
        """

        def all_exists(runs):
            run_names = [run.name for run in
                         self._cc_client.getRunData(None, None, 0, None)]
            print(run_names)
            return set(runs) <= set(run_names)

        def none_exists(runs):
            run_names = [run.name for run in
                         self._cc_client.getRunData(None, None, 0, None)]
            return not bool(set(runs).intersection(run_names))

        # The config database caches the number of runs in a product. We also
        # test whether this cache is accurate, or if the cached number and the
        # actual one diverged due to a bug in CodeChecker.
        def get_run_count_in_config_db():
            get_products_cmd = [self._codechecker_cmd,
                                'cmd', 'products',
                                'list',
                                '-o', 'json',
                                '--url', self.server_url]
            out_products, _ = run_cmd(get_products_cmd, env=check_env)

            ret_products = json.loads(out_products)
            print(ret_products)
            return ret_products[1]['delete_runs']['runCount']

        check_env = self._test_config['codechecker_cfg']['check_env']

        project_name = self._testproject_data['name']
        run2_name = project_name + '_' + str(2)

        # Get all 5 runs.

        self.assertTrue(all_exists(
            [project_name + '_' + str(i) for i in range(0, 5)]))

        # Get runs after run 2 by run name.
        get_runs_cmd = [self._codechecker_cmd,
                        'cmd', 'runs',
                        '--all-after-run', run2_name,
                        '-o', 'json',
                        '--url', self.server_url]
        out_runs, _ = run_cmd(get_runs_cmd, env=check_env)
        ret_runs = json.loads(out_runs)

        self.assertEqual(len(ret_runs), 2)
        self.assertSetEqual({run_name for r in ret_runs for run_name in r},
                            {project_name + '_' + str(i) for i in range(3, 5)})

        self.assertEqual(get_run_count_in_config_db(), 5)
        # Remove runs after run 2 by run name.

        del_cmd = [self._codechecker_cmd,
                   'cmd', 'del',
                   '--all-after-run', run2_name,
                   '--url', self.server_url]
        run_cmd(del_cmd, env=check_env)

        self.assertEqual(get_run_count_in_config_db(), 3)

        self.assertTrue(all_exists(
            [project_name + '_' + str(i) for i in range(0, 3)]))
        self.assertTrue(none_exists(
            [project_name + '_' + str(i) for i in range(3, 5)]))

        # Get runs before run 2 by run date.
        run2 = [run for run in self._cc_client.getRunData(
                    None,
                    None,
                    0,
                    None) if run.name == run2_name][0]

        date_run2 = datetime.strptime(run2.runDate, '%Y-%m-%d %H:%M:%S.%f')
        date_run2 = \
            str(date_run2.year) + ':' + \
            str(date_run2.month) + ':' + \
            str(date_run2.day) + ':' + \
            str(date_run2.hour) + ':' + \
            str(date_run2.minute) + ':' + \
            str(date_run2.second)

        get_runs_cmd = [self._codechecker_cmd,
                        'cmd', 'runs',
                        '--all-before-time', date_run2,
                        '-o', 'json',
                        '--url', self.server_url]
        out_runs, _ = run_cmd(get_runs_cmd, env=check_env)
        ret_runs = json.loads(out_runs)

        self.assertEqual(len(ret_runs), 2)
        self.assertSetEqual({run_name for r in ret_runs for run_name in r},
                            {project_name + '_' + str(i) for i in range(0, 2)})

        # Remove runs before run 2 by run date.
        del_cmd = [self._codechecker_cmd,
                   'cmd', 'del',
                   '--all-before-time', date_run2,
                   '--url', self.server_url]
        run_cmd(del_cmd, env=check_env)

        self.assertTrue(all_exists(
            [project_name + '_' + str(2)]))
        self.assertTrue(none_exists(
            [project_name + '_' + str(i) for i in range(0, 5) if i != 2]))

        # Remove run by run name.

        del_cmd = [self._codechecker_cmd,
                   'cmd', 'del',
                   '--name', run2_name,
                   '--url', self.server_url]
        run_cmd(del_cmd, env=check_env)

        self.assertTrue(none_exists(
            [project_name + '_' + str(i) for i in range(0, 5)]))

        self.assertEqual(get_run_count_in_config_db(), 0)
