#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""dynamic_results function test.

Test the storage and query of dynamic analysis results.
"""

import os
import shutil
import sys
import unittest

from libtest import codechecker
from libtest import env
from libtest import project

from codechecker_api.codeCheckerDBAccess_v6.ttypes import \
    Order, Pair, ReportFilter, SortMode, SortType


class DynamicResults(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing dynamic_results."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('dynamic_results')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        shutil.copytree(
            project.path("dynamic"), TEST_WORKSPACE, dirs_exist_ok=True)

        for plist in os.listdir(TEST_WORKSPACE):
            if plist.endswith('.plist'):
                with open(os.path.join(TEST_WORKSPACE, plist), 'r+',
                          encoding='utf-8',
                          errors='ignore') as plist_file:
                    content = plist_file.read()
                    new_content = content.replace("$FILE_PATH$",
                                                  TEST_WORKSPACE)
                    plist_file.seek(0)
                    plist_file.truncate()
                    plist_file.write(new_content)

        server_access = codechecker.start_or_get_server()
        server_access["viewer_product"] = "dynamic_results"
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        codechecker_cfg = {
            'workspace': TEST_WORKSPACE,
            'reportdir': TEST_WORKSPACE,
            'check_env': env.test_env(TEST_WORKSPACE)
        }

        codechecker_cfg.update(server_access)

        env.export_test_cfg(TEST_WORKSPACE, {
            'codechecker_cfg': codechecker_cfg
        })

        if codechecker.store(codechecker_cfg, "dynamic_results"):
            sys.exit(1)

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, _):
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self.test_cfg = env.import_test_cfg(self.test_workspace)

        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

    def test_sort_by_timestamp(self):
        """
        Test if the reports can be sorted by their "timestamp" attribute.
        """
        results = self._cc_client.getRunResults(
            None, 500, 0, None, ReportFilter(), None, False)

        self.assertEqual(len(results), 4)

        sort_timestamp = SortMode(SortType.TIMESTAMP, Order.ASC)

        results = self._cc_client.getRunResults(
            None, 500, 0, [sort_timestamp], ReportFilter(), None, False)

        # At least one report has a timestamp.
        # Needed for the next sorting test.
        self.assertTrue(any(map(
            lambda report: 'timestamp' in report.annotations, results)))

        for i in range(len(results) - 1):
            if 'timestamp' not in results[i].annotations or \
               'timestamp' not in results[i + 1].annotations:
                continue

            self.assertLess(
                results[i].annotations['timestamp'],
                results[i + 1].annotations['timestamp'])

    def test_filter_by_attribute(self):
        """
        Test if the reports can be filtered by their attributes.
        """
        testcase_filter = ReportFilter(annotations=[Pair(
            first='testcase',
            second='TC-1')])

        results = self._cc_client.getRunResults(
            None, 500, 0, None, testcase_filter, None, False)

        self.assertEqual(len(results), 3)

        self.assertTrue(all(map(
            lambda report: report.annotations['testcase'] == 'TC-1',
            results)))

    def test_count_by_attribute(self):
        """
        Test the report count functions with the usage of report annotations.
        """
        num = self._cc_client.getRunResultCount(
            None, ReportFilter(), None)

        self.assertEqual(num, 4)

        testcase_filter = ReportFilter(annotations=[Pair(
            first='testcase',
            second='TC-1')])

        num = self._cc_client.getRunResultCount(
            None, testcase_filter, None)

        self.assertEqual(num, 3)
