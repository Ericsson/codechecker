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
import subprocess
import tempfile
import unittest

from libtest import env


def run_cmd(cmd, env=None):
    print(cmd)
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="ignore")

    out, err = proc.communicate()
    print(out)
    return proc.returncode, out, err


class TestCmdline(unittest.TestCase):
    """
    Simple tests to check CodeChecker command line.
    """

    def setUp(self):

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

    def test_main_help(self):
        """ Main cmdline help. """

        main_help = [env.codechecker_cmd(), '--help']
        self.assertEqual(0, run_cmd(main_help)[0])

    def test_version_help(self):
        """ Test the 'version' subcommand. """

        version_help = [env.codechecker_cmd(), 'version', '--help']
        self.assertEqual(0, run_cmd(version_help)[0])

    def test_server_help(self):
        """ Get help for server subcmd. """

        srv_help = [env.codechecker_cmd(), 'server', '--help']
        self.assertEqual(0, run_cmd(srv_help)[0])

    def test_sum(self):
        """ Test cmd sum command. """

        sum_res = [self._codechecker_cmd, 'cmd', 'sum',
                   '-a', '--url', str(self.server_url)]

        ret = run_cmd(sum_res,
                      env=self._test_config['codechecker_cfg']['check_env'])[0]
        self.assertEqual(0, ret)

    def test_runs_filter(self):
        """ Test cmd results filter command. """

        env = self._test_config['codechecker_cfg']['check_env']

        # Get runs without filter.
        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'json', '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)

        self.assertEqual(0, ret)
        self.assertEqual(2, len(json.loads(res)))

        # Filter both runs.
        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'json', '-n', 'test_files*',
                   '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)

        self.assertEqual(0, ret)
        self.assertEqual(2, len(json.loads(res)))

        # Filter only one run.
        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'json', '-n', 'test_files1*',
                   '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)

        self.assertEqual(0, ret)
        self.assertEqual(1, len(json.loads(res)))

    def test_proxy_settings(self):
        """ Test proxy settings validation. """
        server_url = f"{self.codechecker_cfg['viewer_host']}:" \
                     f"{str(self.codechecker_cfg['viewer_port'])}"

        env = self.codechecker_cfg['check_env'].copy()
        env['HTTP_PROXY'] = server_url

        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '--url', str(self.server_url)]
        ret, _, err = run_cmd(res_cmd, env=env)
        self.assertEqual(1, ret)
        self.assertIn("Invalid proxy format", err)

        env['HTTP_PROXY'] = f"http://{server_url}"
        _, _, err = run_cmd(res_cmd, env=env)

        # We can't check the return code here, because on host machine it will
        # be zero, but on the GitHub action's job it will be 1 with "Failed to
        # connect to the server" error message.
        self.assertNotIn("Invalid proxy format", err)

    def test_runs_row(self):
        """ Test cmd row output type. """
        env = self._test_config['codechecker_cfg']['check_env']

        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'rows', '-n', 'test_files1*',
                   '--url', str(self.server_url)]
        ret, _, _ = run_cmd(res_cmd, env=env)

        self.assertEqual(0, ret)

    def test_run_update(self):
        """ Test to update run name from the command line. """

        env = self._test_config['codechecker_cfg']['check_env']

        # Get runs.
        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'json', '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)
        self.assertEqual(0, ret)

        runs = json.loads(res)
        self.assertEqual(2, len(runs))

        # Get the first run.
        run = runs[0]
        run_name = list(run.keys())[0]
        new_run_name = "updated#@&_" + run_name

        # Empty string as new name.
        res_cmd = [self._codechecker_cmd, 'cmd', 'update', run_name,
                   '-n', '', '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)
        self.assertEqual(1, ret)

        # Update the run name.
        res_cmd = [self._codechecker_cmd, 'cmd', 'update',
                   '-n', new_run_name, run_name, '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)
        self.assertEqual(0, ret)

        # See that the run was renamed.
        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'json', '-n', run_name,
                   '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)

        self.assertEqual(0, ret)
        self.assertEqual(0, len(json.loads(res)))

        res_cmd = [self._codechecker_cmd, 'cmd', 'update',
                   '-n', new_run_name, new_run_name,
                   '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)
        self.assertEqual(1, ret)

        # Rename the run back to the original name.
        res_cmd = [self._codechecker_cmd, 'cmd', 'update',
                   '-n', run_name, new_run_name, '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)
        self.assertEqual(0, ret)

    def test_results_multiple_runs(self):
        """
        Test cmd results with multiple run names.
        """
        check_env = self._test_config['codechecker_cfg']['check_env']

        res_cmd = [self._codechecker_cmd, 'cmd', 'results', 'test_files1*',
                   'test_files1*', '-o', 'json', '--url', str(self.server_url)]

        ret, _, _ = run_cmd(res_cmd, env=check_env)
        self.assertEqual(0, ret)

    def test_stderr_results(self):
        """
        Test results command that we redirect logger's output to the stderr if
        the given output format is not table.
        """
        check_env = self._test_config['codechecker_cfg']['check_env']

        res_cmd = [self._codechecker_cmd, 'cmd', 'results', 'non_existing_run',
                   '-o', 'json', '--url', str(self.server_url)]

        ret, res, err = run_cmd(res_cmd, env=check_env)
        self.assertEqual(1, ret)
        self.assertEqual(res, '')
        self.assertIn('No runs were found!', err)

    def test_stderr_sum(self):
        """
        Test sum command that we redirect logger's output to the stderr if
        the given output format is not table.
        """
        check_env = self._test_config['codechecker_cfg']['check_env']

        res_cmd = [self._codechecker_cmd, 'cmd', 'sum', '-n',
                   'non_existing_run', '-o', 'json', '--url',
                   str(self.server_url)]

        ret, res, err = run_cmd(res_cmd, env=check_env)
        self.assertEqual(1, ret)
        self.assertEqual(res, '')
        self.assertIn('No runs were found!', err)

    def test_run_sort(self):
        """ Test cmd runs sort command. """

        env = self._test_config['codechecker_cfg']['check_env']

        # Sort runs by the default sort type and sort order.
        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'json',
                   '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)

        self.assertEqual(0, ret)
        self.assertEqual(2, len(json.loads(res)))

        # Sort runs by name.
        res_cmd = [self._codechecker_cmd, 'cmd', 'runs',
                   '-o', 'json',
                   '--sort', 'name',
                   '--order', 'asc',
                   '--url', str(self.server_url)]
        ret, res, _ = run_cmd(res_cmd, env=env)

        self.assertEqual(0, ret)
        self.assertEqual(2, len(json.loads(res)))

    def test_cmd_component_manage(self):
        """ Manage component from command line. """
        component_name = "cmd ஜ۩۞۩ஜ"
        description = "component from command line"
        value = '\n'.join(['+*/divide_zero.cpp',
                           '-*/new_delete.cpp',
                           '-árvíztűrő tükörfúrógép'])

        env = self._test_config['codechecker_cfg']['check_env']

        # Add new source component.
        with tempfile.NamedTemporaryFile() as component_f:
            component_f.write(value.encode('utf-8'))

            add_cmd = [self._codechecker_cmd, 'cmd', 'components', 'add',
                       '--description', description,
                       '-i', component_f.name,
                       component_name,
                       '--url', str(self.server_url)]

            ret, out, _ = run_cmd(add_cmd, env=env)

        self.assertEqual(0, ret)

        # List source components.
        list_cmd = [self._codechecker_cmd, 'cmd', 'components', 'list',
                    '-o', 'json',
                    '--url', str(self.server_url)]

        ret, out, _ = run_cmd(list_cmd, env=env)
        self.assertEqual(0, ret)

        res = json.loads(out)
        self.assertNotEqual(0, len(res))
        self.assertEqual(1,
                         len([r for r in res if r['name'] == component_name]))

        # Remove source component.
        rm_cmd = [self._codechecker_cmd, 'cmd', 'components', 'del',
                  component_name,
                  '--url', str(self.server_url)]

        ret, _, _ = run_cmd(rm_cmd, env=env)
        self.assertEqual(0, ret)
