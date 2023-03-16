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
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import \
    Order, Pair, ReportFilter, SortMode, SortType

from libtest import env


class DiffRemote(unittest.TestCase):
    def setUp(self):
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
            None, 500, 0, None, None, None, False)

        self.assertEqual(len(results), 4)

        sort_timestamp = SortMode(SortType.TIMESTAMP, Order.ASC)

        results = self._cc_client.getRunResults(
            None, 500, 0, [sort_timestamp], None, None, False)

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
