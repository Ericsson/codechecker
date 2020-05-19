#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" statistics collector feature test.  """


import os
import unittest
import shlex

from libtest import env
from libtest.codechecker import call_command

NO_STATISTICS_MESSAGE = "Statistics collector checkers are not supported"


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

        # Get if the package is able to collect statistics or not.
        cmd = [self._codechecker_cmd, 'analyze', '-h']
        output, _ = call_command(cmd, cwd=test_workspace, env=self.env)
        self.stats_capable = '--stats' in output
        print("'analyze' reported statistics collector-compatibility? " +
              str(self.stats_capable))

        test_project_path = self._testproject_data['project_path']
        test_project_build = shlex.split(self._testproject_data['build_cmd'])
        test_project_clean = shlex.split(self._testproject_data['clean_cmd'])

        # Clean the test project before logging the compiler commands.
        output, err = call_command(test_project_clean,
                                   cwd=test_project_path,
                                   env=self.env)
        print(output)
        print(err)

        # Create compilation log used in the tests.
        log_cmd = [self._codechecker_cmd, 'log', '-o', 'compile_command.json',
                   '-b']
        log_cmd.extend(test_project_build)
        output, err = call_command(log_cmd,
                                   cwd=test_project_path,
                                   env=self.env)
        print(output)
        print(err)

    def test_stats(self):
        """
        Enable statistics collection for the analysis.
        """
        if not self.stats_capable:
            self.skipTest(NO_STATISTICS_MESSAGE)

        test_project_path = self._testproject_data['project_path']

        cmd = [self._codechecker_cmd, 'analyze', '-o', 'reports', '--stats',
               'compile_command.json']
        output, err = call_command(cmd, cwd=test_project_path, env=self.env)
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
        output, err = call_command(cmd, cwd=test_project_path, env=self.env)
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
        output, err = call_command(cmd, cwd=test_project_path, env=self.env)
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
        out, err = call_command(cmd, cwd=test_project_path, env=self.env)
        print(out)
        print(err)

        analyze_msg = "Starting static analysis"
        self.assertNotIn(analyze_msg, out)

        cmd = [self._codechecker_cmd, 'analyze', '--stats-use', stats_dir,
               'compile_command.json', '-o', 'reports']
        output, err = call_command(cmd, cwd=test_project_path, env=self.env)
        print(output)
        print(err)
        self.assertIn(analyze_msg, output)

        stat_files = os.listdir(stats_dir)

        self.assertIn('SpecialReturn.yaml', stat_files)
        self.assertIn('UncheckedReturn.yaml', stat_files)
