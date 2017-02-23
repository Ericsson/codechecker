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


def run_cmd(cmd):
    print(cmd)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)

    out, _ = proc.communicate()
    print(out)
    return proc.returncode


class TestCmdline(unittest.TestCase):
    """
    Simple tests to check CodeChecker command line.
    """

    def test_main_help(self):
        """ Main cmdline help. """

        main_help = [env.codechecker_cmd(), '--help']
        assert_equals(0, run_cmd(main_help))

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
