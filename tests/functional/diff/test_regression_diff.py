#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import os
import unittest
import logging

import shared

from codeCheckerDBAccess.ttypes import DiffType
from codeCheckerDBAccess.ttypes import ReportFilter

from libtest.thrift_client_to_db import get_all_run_results
from libtest.debug_printer import print_run_results
from libtest import env

"""
Diff feature tests. Comparing results from two runs.
"""


def get_severity_level(name):
    """
    Convert severity level from the name to value.
    """
    return shared.ttypes.Severity._NAMES_TO_VALUES[name]


class Diff(unittest.TestCase):
    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        test_cfg = env.import_test_cfg(test_workspace)

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        runs = self._cc_client.getRunData()

        test_runs = [run for run in runs if run.name in run_names]
        for r in test_runs:
            print(r)

        # There should be at least two runs for this test.
        self.assertIsNotNone(runs)
        self.assertNotEqual(len(runs), 0)
        self.assertGreaterEqual(len(runs), 2)

        # Name order matters from __init__ !
        self._base_runid = test_runs[0].runId  # base
        self._new_runid = test_runs[1].runId  # new

    def test_get_diff_res_count_new(self):
        """
        Count the new results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res = self._cc_client.getDiffResultCount(base_run_id,
                                                      new_run_id,
                                                      DiffType.NEW,
                                                      [])
        self.assertEqual(diff_res, 0)

    def test_get_diff_res_count_resolved(self):
        """
        Count the resolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res = self._cc_client.getDiffResultCount(base_run_id,
                                                      new_run_id,
                                                      DiffType.RESOLVED,
                                                      [])
        self.assertEqual(diff_res, 0)

    def test_get_diff_res_count_unresolved(self):
        """
        Count the unresolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        base_count = self._cc_client.getRunResultCount(base_run_id, [])
        logging.debug("Base run id: %d", base_run_id)
        logging.debug("Base count: %d", base_count)

        base_run_res = get_all_run_results(self._cc_client, base_run_id)

        print_run_results(base_run_res)

        new_count = self._cc_client.getRunResultCount(new_run_id, [])
        logging.debug("New run id: %d", new_run_id)
        logging.debug("New count: %d", new_count)

        new_run_res = get_all_run_results(self._cc_client, new_run_id)

        print_run_results(new_run_res)

        diff_res = self._cc_client.getDiffResultCount(base_run_id,
                                                      new_run_id,
                                                      DiffType.UNRESOLVED,
                                                      [])
        # Nothing is resolved.
        self.assertEqual(diff_res, base_count)

    def test_get_diff_res_count_unresolved_filter(self):
        """
        This test asumes nothing has been resolved between the two checker
        runs. The the same severity levels and numbers are used as in a
        simple filter test for only one run from the project config.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        # Severity levels used for filtering.
        filter_severity_levels = self._testproject_data[self._clang_to_test][
            'filter_severity_levels']

        for level in filter_severity_levels:
            for severity_level, test_result_count in level.items():
                simple_filters = []
                sev = get_severity_level(severity_level)
                simple_filter = ReportFilter(severity=sev)
                simple_filters.append(simple_filter)

                diff_result_count = self._cc_client.getDiffResultCount(
                    base_run_id, new_run_id, DiffType.UNRESOLVED,
                    simple_filters)

                self.assertEqual(test_result_count, diff_result_count)

    def test_get_diff_res_types_new(self):
        """
        Test diff result types for new results.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res = self._cc_client.getDiffResultTypes(base_run_id,
                                                      new_run_id,
                                                      DiffType.NEW,
                                                      [])
        self.assertEqual(len(diff_res), 0)

    def test_get_diff_res_types_resolved(self):
        """
        Test diff result types for resolved results.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res = self._cc_client.getDiffResultTypes(base_run_id,
                                                      new_run_id,
                                                      DiffType.RESOLVED,
                                                      [])
        self.assertEqual(len(diff_res), 0)

    def test_get_diff_res_types_unresolved(self):
        """
        Test diff result types for unresolved results with no filter
        on the api.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res_types_filter = self._testproject_data[self._clang_to_test][
            'diff_res_types_filter']

        for level in diff_res_types_filter:
            for checker_name, test_result_count in level.items():
                diff_res = \
                    self._cc_client.getDiffResultTypes(base_run_id,
                                                       new_run_id,
                                                       DiffType.UNRESOLVED,
                                                       [])
                res = [r for r in diff_res if r.checkerId == checker_name]

                print("Test cfg - " + checker_name +
                      " : " + str(test_result_count))
                print("Analysis - " + res[0].checkerId +
                      " : " + str(res[0].count))

                # There should be only one result for each checker name.
                self.assertEqual(len(res), 1)
                self.assertEqual(test_result_count, res[0].count)
                self.assertEqual(checker_name, res[0].checkerId)

    def test_get_diff_res_types_unresolved_filter(self):
        """
        Test diff result types for unresolved results with checker name filter
        on the api.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res_types_filter = self._testproject_data[self._clang_to_test][
            'diff_res_types_filter']

        for level in diff_res_types_filter:
            for checker_name, test_result_count in level.items():
                simple_filters = []
                simple_filter = ReportFilter(checkerId=checker_name)
                simple_filters.append(simple_filter)

                diff_res = \
                    self._cc_client.getDiffResultTypes(base_run_id,
                                                       new_run_id,
                                                       DiffType.UNRESOLVED,
                                                       simple_filters)

                print("Test cfg - " + checker_name +
                      " : " + str(test_result_count))
                print("Analysis - " + diff_res[0].checkerId +
                      " : " + str(diff_res[0].count))

                # There should be only one for each checker name.
                self.assertEqual(len(diff_res), 1)
                self.assertEqual(test_result_count, diff_res[0].count)
                self.assertEqual(checker_name, diff_res[0].checkerId)
