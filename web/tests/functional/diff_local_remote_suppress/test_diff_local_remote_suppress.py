#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""diff_local_remote function test.

Tests for the diff feature when comparing a local report directory
with a remote run in the database. These tests are for differences
based on bug suppressions especially.
"""


import os
import unittest

from libtest import env
from libtest.codechecker import get_diff_results

from . import setup_class_common, teardown_class_common


class DiffLocalRemoteSuppress(unittest.TestCase):

    def setup_class(self):
        setup_class_common("diff_local_remote_suppress")

    def teardown_class(self):
        teardown_class_common()

    def setup_method(self, method):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        self._test_cfg = env.import_test_cfg(test_workspace)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        # Get the run names which belong to this test.
        self._run_names = env.get_run_names(test_workspace)

        self._project_path_orig = \
            self._test_cfg['test_project']['project_path_orig']
        self._project_path_1 = \
            self._test_cfg['test_project']['project_path_1']
        self._project_path_2 = \
            self._test_cfg['test_project']['project_path_2']

        self._report_dir_orig = \
            os.path.join(self._project_path_orig, 'reports')
        self._report_dir_1 = os.path.join(self._project_path_1, 'reports')
        self._report_dir_2 = os.path.join(self._project_path_2, 'reports')

        self._url = env.parts_to_url(self._test_cfg['codechecker_cfg'])

        self._env = self._test_cfg['codechecker_cfg']['check_env']

    @staticmethod
    def filter_by_checker(results, checker_name):
        return list(filter(
            lambda report: report['checker_name'] == checker_name,
            results))

    def test_local_remote_new(self):
        """
        Suppressed reports are considered as closed in the new check in a
        local-remote diff when querying new reports.
        """
        results = get_diff_results(
            [self._report_dir_orig], [self._run_names['test_project_2']],
            '--new', 'json',
            ['--url', self._url])[0]

        self.assertEqual(len(results), 0)

    def test_local_remote_resolved(self):
        """
        Suppressed reports are considered as closed in the new check in a
        local-remote diff when querying resolved reports.
        """
        results = get_diff_results(
            [self._report_dir_orig], [self._run_names['test_project_2']],
            '--resolved', 'json',
            ['--url', self._url])[0]

        self.assertEqual(
            len(results), 7)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.CallAndMessage')), 5)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.DivideZero')), 1)
        self.assertEqual(
            len(self.filter_by_checker(results, 'deadcode.DeadStores')), 1)

    def test_local_remote_unresolved(self):
        """
        Suppressed reports are considered as closed in the baseline and in new
        check in a local-remote diff when querying unresolved reports.
        """
        results = get_diff_results(
            [self._report_dir_orig], [self._run_names['test_project_2']],
            '--unresolved', 'json',
            ['--url', self._url])[0]

        self.assertEqual(
            len(results), 27)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.DivideZero')), 9)
        self.assertEqual(
            len(self.filter_by_checker(results, 'deadcode.DeadStores')), 5)
        self.assertEqual(
            len(self.filter_by_checker(results, 'cplusplus.NewDelete')), 5)
        self.assertEqual(
            len(self.filter_by_checker(results, 'unix.Malloc')), 1)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.StackAddressEscape')), 3)

    def test_remote_local_new(self):
        """
        Suppressed reports are considered as closed in the baseline in a
        remote-local diff when querying new reports.
        """
        results = get_diff_results(
            [self._run_names['test_project_2']], [self._report_dir_orig],
            '--new', 'json',
            ['--url', self._url])[0]

        self.assertEqual(
            len(results), 7)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.CallAndMessage')), 5)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.DivideZero')), 1)
        self.assertEqual(
            len(self.filter_by_checker(results, 'deadcode.DeadStores')), 1)

    def test_remote_local_resolved(self):
        """
        Suppressed reports are considered as closed in the baseline in a
        remote-local diff when querying resolved reports.
        """
        results = get_diff_results(
            [self._run_names['test_project_2']], [self._report_dir_orig],
            '--resolved', 'json',
            ['--url', self._url])[0]

        self.assertEqual(len(results), 0)

    def test_remote_local_unresolved(self):
        """
        Suppressed reports are considered as closed in the baseline and in new
        check in a remote-local diff when querying unresolved reports.
        """
        results = get_diff_results(
            [self._run_names['test_project_2']], [self._report_dir_orig],
            '--unresolved', 'json',
            ['--url', self._url])[0]

        self.assertEqual(
            len(results), 27)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.DivideZero')), 9)
        self.assertEqual(
            len(self.filter_by_checker(results, 'deadcode.DeadStores')), 5)
        self.assertEqual(
            len(self.filter_by_checker(results, 'cplusplus.NewDelete')), 5)
        self.assertEqual(
            len(self.filter_by_checker(results, 'unix.Malloc')), 1)
        self.assertEqual(
            len(self.filter_by_checker(results, 'core.StackAddressEscape')), 3)
