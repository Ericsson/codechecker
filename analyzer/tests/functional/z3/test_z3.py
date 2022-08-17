#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Z3 feature test.  """


from distutils import util
import os
import unittest
import shlex

from libtest import env
from libtest.codechecker import call_command

NO_Z3_MESSAGE = "Z3 is not supported"


class TestSkeleton(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        self.env = env.codechecker_env()

        # Get if the package is z3 compatible.
        cmd = [self._codechecker_cmd, 'analyze', '-h']
        output, _, _ = call_command(cmd, cwd=test_workspace, env=self.env)
        self.z3_capable = '--z3' in output
        print(f"'analyze' reported z3 compatibility? {self.z3_capable}")

        if not self.z3_capable:
            try:
                self.z3_capable = bool(util.strtobool(
                    os.environ['CC_TEST_FORCE_Z3_CAPABLE']))
            except (ValueError, KeyError):
                pass

        test_project_path = self._testproject_data['project_path']
        test_project_build = shlex.split(self._testproject_data['build_cmd'])
        test_project_clean = shlex.split(self._testproject_data['clean_cmd'])

        # Clean the test project before logging the compiler commands.
        output, err, _ = call_command(
            test_project_clean, cwd=test_project_path, env=self.env)
        print(output)
        print(err)

        # Create compilation log used in the tests.
        log_cmd = [
            self._codechecker_cmd, 'log', '-o', 'compile_command.json', '-b']
        log_cmd.extend(test_project_build)
        output, err, _ = call_command(
            log_cmd, cwd=test_project_path, env=self.env)
        print(output)
        print(err)

    def test_z3(self):
        """ Enable z3 during analysis. """
        if not self.z3_capable:
            self.skipTest(NO_Z3_MESSAGE)

        test_project_path = self._testproject_data['project_path']

        cmd = [
            self._codechecker_cmd, 'analyze',
            'compile_command.json',
            '-o', 'reports',
            '--z3', 'on',
            '--verbose', 'debug']
        output, _, ret = call_command(
            cmd, cwd=test_project_path, env=self.env)
        self.assertEqual(ret, 0)
        self.assertIn("-analyzer-constraints=z3", output)

    def test_z3_refutation(self):
        """ Enable z3 refutation during analysis. """
        if not self.z3_capable:
            self.skipTest(NO_Z3_MESSAGE)

        test_project_path = self._testproject_data['project_path']

        cmd = [
            self._codechecker_cmd, 'analyze',
            'compile_command.json',
            '-o', 'reports',
            '--z3-refutation', 'on',
            '--verbose', 'debug']
        output, _, ret = call_command(
            cmd, cwd=test_project_path, env=self.env)
        self.assertEqual(ret, 0)
        self.assertIn("crosscheck-with-z3=true", output)
