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
import unittest
import subprocess
from datetime import datetime

from libtest import env


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
