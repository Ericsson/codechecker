#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" statistics collector feature test.  """


from codechecker_common.util import strtobool
import os
import shutil
import sys
import shlex
import unittest

from libtest import env
from libtest import project
from libtest.codechecker import call_command

NO_STATISTICS_MESSAGE = "Statistics collector checkers are not supported"


class TestSkeleton(unittest.TestCase):

    _ccClient = None

    def setup_class(self):
        """Setup the environment for testing statistics."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('statistics')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        test_project = 'cpp'

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
            'checkers': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        # Clean the test project, if needed by the tests.
        ret = project.clean(test_project)
        if ret:
            sys.exit(ret)

        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE, test_config)

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, _):

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

        test_project_path = self._testproject_data['project_path']
        test_project_build = shlex.split(self._testproject_data['build_cmd'])
        test_project_clean = shlex.split(self._testproject_data['clean_cmd'])

        # Clean the test project before logging the compiler commands.
        out, err = call_command(test_project_clean,
                                cwd=test_project_path,
                                environ=self.env)
        print(out)
        print(err)

        # Create compilation log used in the tests.
        log_cmd = [self._codechecker_cmd, 'log', '-o', 'compile_command.json',
                   '-b']
        log_cmd.extend(test_project_build)
        out, err = call_command(log_cmd,
                                cwd=test_project_path,
                                environ=self.env)
        print(out)
        print(err)

        # Get if the package is able to collect statistics or not.
        cmd = [self._codechecker_cmd,
               'analyze', 'compile_command.json',
               '-o', 'reports',
               '--stats']

        out, _ = call_command(cmd, cwd=test_project_path, environ=self.env)

        self.stats_capable = \
            'Statistics options can only be enabled' not in out

        print("'analyze' reported statistics collector-compatibility? " +
              str(self.stats_capable))

        if not self.stats_capable:
            try:
                self.stats_capable = strtobool(
                    os.environ['CC_TEST_FORCE_STATS_CAPABLE']
                )
            except (ValueError, KeyError):
                pass

    def test_stats(self):
        """
        Enable statistics collection for the analysis.
        """
        if not self.stats_capable:
            self.skipTest(NO_STATISTICS_MESSAGE)

        test_project_path = self._testproject_data['project_path']

        cmd = [self._codechecker_cmd, 'analyze', '-o', 'reports', '--stats',
               'compile_command.json']
        output, err = call_command(
            cmd,
            cwd=test_project_path,
            environ=self.env)
        print(output)
        print(err)
        collect_msg = "Collecting data for statistical analysis."
        self.assertIn(collect_msg, output)

    def test_stats_collect(self):
        """
        Enable statistics collection.
        Without analysis.
        """
        if not self.stats_capable:
            self.skipTest(NO_STATISTICS_MESSAGE)

        test_project_path = self._testproject_data['project_path']
        stats_dir = os.path.join(test_project_path, 'stats')
        cmd = [self._codechecker_cmd, 'analyze', '--stats-collect', stats_dir,
               'compile_command.json', '-o', 'reports']
        output, err = call_command(
            cmd,
            cwd=test_project_path,
            environ=self.env)
        print(output)
        print(err)
        analyze_msg = "Starting static analysis"
        self.assertNotIn(analyze_msg, output)
        stat_files = os.listdir(stats_dir)
        print(stat_files)
        self.assertIn('SpecialReturn.yaml', stat_files)
        self.assertIn('UncheckedReturn.yaml', stat_files)

    def test_stats_collect_params(self):
        """
        Testing collection parameters
        """
        if not self.stats_capable:
            self.skipTest(NO_STATISTICS_MESSAGE)

        test_project_path = self._testproject_data['project_path']
        stats_dir = os.path.join(test_project_path, 'stats')
        cmd = [self._codechecker_cmd, 'analyze', '--stats-collect', stats_dir,
               'compile_command.json',
               '--stats-min-sample-count', '10',
               '--stats-relevance-threshold', '0.8',
               '-o', 'reports']
        output, err = call_command(
            cmd,
            cwd=test_project_path,
            environ=self.env)
        print(output)
        print(err)
        analyze_msg = "Starting static analysis"
        self.assertNotIn(analyze_msg, output)
        stat_files = os.listdir(stats_dir)
        print(stat_files)
        self.assertIn('SpecialReturn.yaml', stat_files)
        self.assertIn('UncheckedReturn.yaml', stat_files)
        with open(os.path.join(stats_dir, 'UncheckedReturn.yaml'), 'r',
                  encoding="utf-8", errors="ignore") as statfile:
            unchecked_stats = statfile.read()
        self.assertIn("c:@F@readFromFile#*1C#*C#", unchecked_stats)

    def test_stats_use(self):
        """
        Use the already collected statistics for the analysis.
        """
        if not self.stats_capable:
            self.skipTest(NO_STATISTICS_MESSAGE)

        test_project_path = self._testproject_data['project_path']
        stats_dir = os.path.join(test_project_path, 'stats')
        cmd = [self._codechecker_cmd, 'analyze', '--stats-collect', stats_dir,
               'compile_command.json', '-o', 'reports']
        out, err = call_command(cmd, cwd=test_project_path, environ=self.env)
        print(out)
        print(err)

        analyze_msg = "Starting static analysis"
        self.assertNotIn(analyze_msg, out)

        cmd = [self._codechecker_cmd, 'analyze', '--stats-use', stats_dir,
               'compile_command.json', '-o', 'reports']
        output, err = call_command(
            cmd,
            cwd=test_project_path,
            environ=self.env)
        print(output)
        print(err)
        self.assertIn(analyze_msg, output)

        stat_files = os.listdir(stats_dir)

        self.assertIn('SpecialReturn.yaml', stat_files)
        self.assertIn('UncheckedReturn.yaml', stat_files)
