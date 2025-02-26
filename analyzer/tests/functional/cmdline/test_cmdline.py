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
import unittest

from libtest import env


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


class TestCmdline(unittest.TestCase):
    """
    Simple tests to check CodeChecker command line.
    """

    def __init__(self, methodName):
        self.test_workspace = None
        self._codechecker_cmd = None
        super().__init__(methodName)

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('cmdline')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    def teardown_class(self):
        """Delete the workspace associated with this test"""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def setup_method(self, _):
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

    def test_invalid_subcommand(self):
        """ Call CodeChecker with and invalid subcommand. """

        dummy_cmd = [env.codechecker_cmd(), "dummy"]
        self.assertEqual(1, run_cmd(dummy_cmd)[0])

    def test_checkers(self):
        """ Listing available checkers. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers']
        self.assertEqual(0, run_cmd(checkers_cmd)[0])

    def test_checkers_profile(self):
        """ Listing available checker profiles. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers', '--profile']
        out = run_cmd(checkers_cmd)
        self.assertEqual(0, out[0])
        self.assertEqual(True, "default" in out[1])

    def test_checkers_label(self):
        """ Listing checkers with given label. """

        checkers_cmd = [env.codechecker_cmd(), 'checkers', '--label']
        exit_code, out, _ = run_cmd(checkers_cmd)
        self.assertEqual(0, exit_code)
        self.assertIn('profile', out)
        self.assertIn('severity', out)
        self.assertIn('guideline', out)

        checkers_cmd = [
            env.codechecker_cmd(), 'checkers', '--label', 'severity']
        exit_code, out, _ = run_cmd(checkers_cmd)
        self.assertEqual(0, exit_code)
        self.assertIn('HIGH', out)
        self.assertIn('MEDIUM', out)
        self.assertIn('LOW', out)

        checkers_cmd = [
            env.codechecker_cmd(), 'checkers', '--label', 'severity:HIGH']
        exit_code, out, _ = run_cmd(checkers_cmd)
        self.assertEqual(0, exit_code)
        self.assertIn('core.DivideZero', out)
        self.assertIn('core.CallAndMessage', out)

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
                        '--guideline', 'sei-cert-cpp']
        _, out, _ = run_cmd(checkers_cmd)

        self.assertIn('cert-dcl58-cpp', out)
        self.assertNotIn('android', out)

        checkers_cmd = [env.codechecker_cmd(), 'checkers',
                        '--guideline', 'sei-cert-c:mem35-c']
        _, out, _ = run_cmd(checkers_cmd)

        self.assertIn('MallocSizeof', out)
        self.assertNotIn('CastToStruct', out)

        checkers_cmd = [env.codechecker_cmd(), 'checkers',
                        '--guideline', 'sei-cert-c:mem35-c', '-o', 'json',
                        '--details']
        _, out, _ = run_cmd(checkers_cmd)
        out = json.loads(out)

        for checker in out:
            self.assertTrue(any(checker['name'].endswith(c)
                            for c in ['sizeof-expression',
                                      'Malloc',
                                      'MallocSizeof',
                                      'clang-diagnostic-format-overflow',
                                      'overflow-non-kprintf']))

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
        self.assertNotIn('GREEN', out)

        # --warnings flag is deprecated. Warnings are included in checker list
        # by default.
        checkers_cmd = [env.codechecker_cmd(), 'checkers']
        retcode, out, _ = run_cmd(checkers_cmd)

        self.assertEqual(retcode, 0)
        self.assertIn('clang-diagnostic-vla', out)
        # Make sure the header from `diagtool --tree` is ignored.
        self.assertNotIn('GREEN', out)

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

    def test_parse_incorrect_file_path(self):
        """
        This test checks whether the parse command stops running if a
        non-existent path is specified.
        """

        parse_cmd = [env.codechecker_cmd(), 'parse', '/asd/123/qwe']

        self.assertIn('Input path /asd/123/qwe does not exist!',
                      run_cmd(parse_cmd)[1])

    def test_analyze_incorrect_checker_analyzer(self):
        """
        This test checks whether the analyze command stops running if a
        non-existent path is specified.
        """
        test_file = os.path.join(self.test_workspace, 'main.cpp')

        with open(test_file, 'w', encoding="utf-8", errors="ignore") as f:
            f.write("int main() {}")

        cmd_err = [env.codechecker_cmd(), 'check',
                   '--analyzer-config', 'clang:asd=1',
                   '--checker-config', 'clang:asd:asd=1',
                   '--build', f'g++ {test_file}']

        cmd_no_err = [env.codechecker_cmd(), 'check',
                      '--analyzer-config', 'clang:asd=1',
                      '--checker-config', 'clang:asd:asd=1',
                      '--no-missing-checker-error',
                      '--build', f'g++ {test_file}']

        self.assertEqual(1, run_cmd(cmd_err)[0])
        self.assertIn('Build finished successfully', run_cmd(cmd_no_err)[1])

    def test_checker_config_format(self):
        """
        Test if checker config option is meeting the reqired format.
        """
        test_file = os.path.join(self.test_workspace, 'main.cpp')

        with open(test_file, 'w', encoding="utf-8", errors="ignore") as f:
            f.write("int main() {}")

        cmd = [env.codechecker_cmd(), 'check',
               '--checker-config', 'clangsa:checker.option=value',
               '-b', f'g++ {test_file}']

        return_code, _, err = run_cmd(cmd)

        self.assertEqual(return_code, 1)
        self.assertIn("Checker option in wrong format", err)

        cmd = [env.codechecker_cmd(), 'check',
               '--checker-config', 'clangsa:checker:option=value',
               '-b', f'g++ {test_file}']

        _, _, err = run_cmd(cmd)

        self.assertNotIn("Checker option in wrong format", err)
