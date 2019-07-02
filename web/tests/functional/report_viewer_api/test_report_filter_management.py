#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test report filter management.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

from libtest import env


class TestReportFilterManagement(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

    def test_invalid_report_filter(self):
        """
        Try to add report filters which have an invalid formatted value and
        check that these filters are not created on the server.
        """
        ret = self._cc_client.addReportFilter('test', '')
        self.assertEqual(ret, False)

        ret = self._cc_client.addReportFilter('test', '{invalid: json')
        self.assertEqual(ret, False)

        report_filters = self._cc_client.getReportFilters(None)
        self.assertEqual(len(report_filters), 0)

    def test_add_and_remove_report_filter(self):
        """
        Try to add a new report filter, get the available report filter to
        see that it is stored in the database and finally remove this filter.
        """
        ret = self._cc_client.addReportFilter('test1', '{}')
        self.assertEqual(ret, True)

        report_filters = self._cc_client.getReportFilters(None)
        self.assertEqual(len(report_filters), 1)
        self.assertEqual(report_filters[0].name, 'test1')
        self.assertEqual(report_filters[0].value, '{}')

        ret = self._cc_client.removeReportFilter(report_filters[0].id)
        self.assertEqual(ret, True)

        report_filters = self._cc_client.getReportFilters(None)
        self.assertEqual(len(report_filters), 0)

    def test_filter_report_filter(self):
        """
        Test filtering report filters.
        """
        filter_value_1 = '{\"severity\":[\"High\"]}'
        ret = self._cc_client.addReportFilter('test1', filter_value_1)
        self.assertEqual(ret, True)

        filter_value_2 = '{\"severity\":[\"Low\"]}'
        ret = self._cc_client.addReportFilter('test2', filter_value_2)
        self.assertEqual(ret, True)

        all_report_filters = self._cc_client.getReportFilters(None)
        self.assertEqual(len(all_report_filters), 2)

        report_filters = self._cc_client.getReportFilters("test*")
        self.assertEqual(len(report_filters), 2)

        report_filters = self._cc_client.getReportFilters("test1")
        self.assertEqual(len(report_filters), 1)
        self.assertEqual(report_filters[0].name, 'test1')
        self.assertEqual(report_filters[0].value, filter_value_1)

        for report_filter in all_report_filters:
            ret = self._cc_client.removeReportFilter(report_filter.id)
            self.assertEqual(ret, True)
