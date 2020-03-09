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
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

    def test_no_subcommand(self):
        """ Call CodeChecker without subcommand. """

        main_cmd = [env.codechecker_cmd()]
        self.assertEqual(0, run_cmd(main_cmd)[0])

    def test_version_help(self):
        """ Test the 'analyzer-version' subcommand. """

        version_help = [env.codechecker_cmd(), 'analyzer-version', '--help']
        self.assertEqual(0, run_cmd(version_help)[0])

    def test_check_help(self):
        """ Get help for check subcmd. """

        check_help = [env.codechecker_cmd(), 'check', '--help']
        self.assertEqual(0, run_cmd(check_help)[0])

    def test_log_help(self):
        """ Get help for log subcmd. """

        log_help = [env.codechecker_cmd(), 'log', '--help']
        self.assertEqual(0, run_cmd(log_help)[0])

    def test_analyze_help(self):
        """ Get help for analyze subcmd. """

        analyze_help = [env.codechecker_cmd(), 'analyze', '--help']
        self.assertEqual(0, run_cmd(analyze_help)[0])

    def test_parse_help(self):
        """ Get help for parse subcmd. """

        parse_help = [env.codechecker_cmd(), 'parse', '--help']
        self.assertEqual(0, run_cmd(parse_help)[0])

    def test_checkers(self):
        """ Listing available checkers. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers']
        self.assertEqual(0, run_cmd(checkers_cmd)[0])

    def test_analyzers(self):
        """ Listing available analyzers. """

        analyzers_cmd = [env.codechecker_cmd(), 'analyzers']
        self.assertEqual(0, run_cmd(analyzers_cmd)[0])
