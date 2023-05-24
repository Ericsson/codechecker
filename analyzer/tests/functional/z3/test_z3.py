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
import shutil
import unittest
import shlex

from libtest import env, codechecker, project
from libtest.codechecker import call_command

NO_Z3_MESSAGE = "Z3 is not supported"


class TestSkeleton(unittest.TestCase):

    _ccClient = None

    def setup_class():
        """Setup the environment for testing z3."""
    
        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('z3')
    
        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE
    
        test_config = {}
    
        test_project = 'suppress'
    
        project_info = project.get_info(test_project)
    
        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(project.path(test_project), test_proj_path)
    
        project_info['project_path'] = test_proj_path
    
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
            'checkers': []
        }
    
        # Clean the test project, if needed by the tests.
        ret = project.clean(test_project)
        if ret:
            sys.exit(ret)
    
        test_config['codechecker_cfg'] = codechecker_cfg
    
        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE, test_config)
    
    
    def teardown_class():
        """Clean up after the test."""
    
        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE
    
        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, method):

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
