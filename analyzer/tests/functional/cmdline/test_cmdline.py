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

    def test_checkers_profile(self):
        """ Listing available checker profiles. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers', '--profile', 'list']
        out = run_cmd(checkers_cmd)
        self.assertEqual(0, out[0])
        self.assertEqual(True, "default" in out[1])

    def test_analyzers(self):
        """ Listing available analyzers. """

        analyzers_cmd = [env.codechecker_cmd(), 'analyzers']
        self.assertEqual(0, run_cmd(analyzers_cmd)[0])

    def test_log_empty_build_command(self):
        """ Logging empty build command result will be a valid json file. """

        log_file = os.path.join(self.test_workspace, 'build.json')

        analyzers_cmd = [env.codechecker_cmd(), 'log',
                         '-b', '',
                         '-o', log_file]
        out = run_cmd(analyzers_cmd)
        print(out)

        self.assertTrue(os.path.exists(log_file))
        with open(log_file,
                  encoding="utf-8", errors="ignore") as log_f:
            self.assertFalse(json.load(log_f))

    def test_checkers_guideline(self):
        """ Listing checkers by guideline. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers',
                        '--guideline', 'sei-cert']
        _, out, _ = run_cmd(checkers_cmd)

        self.assertNotIn('readability', out)
        self.assertIn('cert-str34-c', out)

        checkers_cmd = [env.codechecker_cmd(), 'checkers',
                        '--guideline', 'mem35-c']
        _, out, _ = run_cmd(checkers_cmd)

        self.assertIn('MallocSizeof', out)
        self.assertNotIn('CastToStruct', out)

        checkers_cmd = [env.codechecker_cmd(), 'checkers',
                        '--guideline', 'mem35-c', '-o', 'json', '--details']
        _, out, _ = run_cmd(checkers_cmd)
        out = json.loads(out)

        for checker in out:
            self.assertTrue(checker['name'].endswith('sizeof-expression') or
                            checker['name'].endswith('SizeofPtr') or
                            checker['name'].endswith('CastSize') or
                            checker['name'].endswith('MallocSizeof'))

        checkers_cmd = [env.codechecker_cmd(), 'checkers', '--guideline']
        _, out, _ = run_cmd(checkers_cmd)

        self.assertTrue(out.strip().startswith('Guideline: sei-cert'))

    def test_checkers_warnings(self):
        """ Listing checkers for compiler warnings. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers', '--warnings']
        retcode, out, _ = run_cmd(checkers_cmd)

        self.assertEqual(retcode, 0)
        self.assertIn('clang-diagnostic-vla', out)
        # Make sure the header from `diagtool --tree` is ignored.
        self.assertNotIn('EEN', out)

    def test_clangsa_checkers_description(self):
        """
        Test that descriptions for clangsa checkers are parsed properly.
        """
        checkers_cmd = [env.codechecker_cmd(), 'checkers',
                        '--analyzers', 'clangsa',
                        '-o', 'json', '--details']

        _, out, _ = run_cmd(checkers_cmd)
        checkers = json.loads(out)

        for checker in checkers:
            desc = checker['description']
            self.assertTrue(desc)
            self.assertFalse(desc[0].islower())

    def test_checker_config(self):
        """
        Test that descriptions for clangsa checkers configs are parsed
        properly.
        """
        checker_cfg_cmd = [env.codechecker_cmd(), 'checkers',
                           '--analyzers', 'clangsa', '--checker-config',
                           '-o', 'json', '--details']

        _, out, _ = run_cmd(checker_cfg_cmd)
        checker_cfg = json.loads(out)

        for cfg in checker_cfg:
            desc = cfg['description']
            self.assertTrue(desc)
            self.assertFalse(desc[0].islower())

    def test_analyzer_config(self):
        """
        Test that descriptions for clangsa analyzer configs are parsed
        properly.
        """
        analyzer_cfg_cmd = [env.codechecker_cmd(), 'analyzers',
                            '--analyzer-config', 'clangsa',
                            '-o', 'json', '--details']

        _, out, _ = run_cmd(analyzer_cfg_cmd)
        analyzer_cfg = json.loads(out)

        for cfg in analyzer_cfg:
            desc = cfg['description']
            self.assertTrue(desc)
            self.assertFalse(desc[0].islower())
