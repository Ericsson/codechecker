# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the CodeChecker command line.
"""

import os
import subprocess
import unittest

from nose.tools import assert_equals

from libtest import env


def run_cmd(cmd, env=None):
    print(cmd)
    proc = subprocess.Popen(cmd,
                            env=env,
                            stdout=subprocess.PIPE)

    out, _ = proc.communicate()
    print(out)
    return proc.returncode


class TestCmdline(unittest.TestCase):
    """
    Simple tests to check CodeChecker command line.
    """

    def setUp(self):

        test_workspace = os.environ.get('TEST_WORKSPACE')

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

    def test_main_help(self):
        """ Main cmdline help. """

        main_help = [env.codechecker_cmd(), '--help']
        assert_equals(0, run_cmd(main_help))

    def test_version_help(self):
        """ Test the 'version' subcommand. """

        version_help = [env.codechecker_cmd(), 'version', '--help']
        assert_equals(0, run_cmd(version_help))

    def test_check_help(self):
        """ Get help for check subcmd. """

        check_help = [env.codechecker_cmd(), 'check', '--help']
        assert_equals(0, run_cmd(check_help))

    def test_server_help(self):
        """ Get help for server subcmd. """

        srv_help = [env.codechecker_cmd(), 'server', '--help']
        assert_equals(0, run_cmd(srv_help))

    def test_checkers(self):
        """ Listing available checkers. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers']
        assert_equals(0, run_cmd(checkers_cmd))

    def test_sum(self):
        """ Test cmd sum command. """

        sum_res = [self._codechecker_cmd, 'cmd', 'sum',
                   '-a', '--url', str(self.server_url)]

        assert_equals(0, run_cmd(sum_res,
                      env=self._test_config['codechecker_cfg']['check_env']))
