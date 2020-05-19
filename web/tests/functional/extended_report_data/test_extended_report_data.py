#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test extended report data.
"""


import os
import unittest

from libtest import env

from codechecker_api.codeCheckerDBAccess_v6.ttypes import RunFilter, \
    ExtendedReportDataType


class TestExtendedReportData(unittest.TestCase):

    def setUp(self):
        self._test_workspace = os.environ.get('TEST_WORKSPACE')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test
        run_names = env.get_run_names(self._test_workspace)

        runs = self._cc_client.getRunData(None, None, 0, None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 2,
                         'There should be two runs for this test.')

    def __get_run_results(self, run_name):
        """
        Returns list of reports for the given run name.
        """
        run_filter = RunFilter()
        run_filter.names = [run_name]
        run_filter.exactMatch = True

        runs = self._cc_client.getRunData(run_filter, None, 0, None)
        run_id = runs[0].runId

        return self._cc_client.getRunResults([run_id], None, 0, [], None, None,
                                             False)

    def test_notes(self):
        """
        Test whether notes are stored for the reports.
        """
        reports = self.__get_run_results('notes')
        self.assertEqual(len(reports), 1)

        details = self._cc_client.getReportDetails(reports[0].reportId)
        extended_data = details.extendedData[0]
        self.assertEqual(extended_data.type, ExtendedReportDataType.NOTE)

        file_name = os.path.basename(extended_data.filePath)
        self.assertEqual(file_name, "notes.cpp")

    def test_macros(self):
        """
        Test whether macro expansions are stored for the reports.
        """
        reports = self.__get_run_results('macros')
        self.assertEqual(len(reports), 1)

        details = self._cc_client.getReportDetails(reports[0].reportId)
        extended_data = details.extendedData[0]
        self.assertEqual(extended_data.type, ExtendedReportDataType.MACRO)

        file_name = os.path.basename(extended_data.filePath)
        self.assertEqual(file_name, "macros.cpp")
