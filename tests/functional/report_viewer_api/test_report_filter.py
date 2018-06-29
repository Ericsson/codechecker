#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test report filtering.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging
import os
import unittest

from codeCheckerDBAccess_v6.ttypes import *

from libtest import env


def get_severity_level(name):
    """ Convert severity name to value. """
    return Severity._NAMES_TO_VALUES[name]


def get_status(name):
    """ Convert review status name to value. """
    return ReviewStatus._NAMES_TO_VALUES[name]


class TestReportFilter(unittest.TestCase):

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

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]
        self._runids = [r.runId for r in test_runs]

    def test_filter_none(self):
        """ Filter value is None should return all results."""
        runid = self._runids[0]
        sort_types = None
        simple_filters = None

        run_result_count = self._cc_client.getRunResultCount([runid],
                                                             simple_filters,
                                                             None)
        self.assertIsNotNone(run_result_count)

        run_results = self._cc_client.getRunResults([runid],
                                                    run_result_count,
                                                    0,
                                                    sort_types,
                                                    simple_filters,
                                                    None)
        self.assertIsNotNone(run_results)
        self.assertEqual(run_result_count, len(run_results))

    def test_filter_empty(self):
        """ Filter value is empty list should return all results."""
        runid = self._runids[0]
        sort_types = None

        f = ReportFilter()
        run_result_count = self._cc_client.getRunResultCount([runid],
                                                             f,
                                                             None)
        self.assertIsNotNone(run_result_count)

        run_results = self._cc_client.getRunResults([runid],
                                                    run_result_count,
                                                    0,
                                                    sort_types,
                                                    f,
                                                    None)
        self.assertIsNotNone(run_results)
        self.assertEqual(run_result_count, len(run_results))

    def test_filter_severity(self):
        """ Filter by severity levels."""
        runid = self._runids[0]

        severity_test_data = self._testproject_data[self._clang_to_test][
            'filter_severity_levels']

        for level in severity_test_data:
            for severity_level, test_result_count in level.items():
                logging.debug('Severity level filter ' + severity_level +
                              ' test result count: ' + str(test_result_count))
                sort_types = None
                sev = get_severity_level(severity_level)
                sev_f = ReportFilter(severity=[sev])

                run_result_count = self._cc_client.getRunResultCount(
                    [runid], sev_f, None)
                run_results = self._cc_client.getRunResults(
                    [runid], run_result_count, 0, sort_types, sev_f, None)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_filter_checker_id(self):
        """ Filter by checker id. """
        runid = self._runids[0]

        severity_test_data = self._testproject_data[self._clang_to_test][
            'filter_checker_id']

        for level in severity_test_data:
            for checker_id_filter, test_result_count in level.items():
                logging.debug('Checker id filter ' + checker_id_filter +
                              ' test result count: ' + str(test_result_count))
                sort_types = None
                cid_f = ReportFilter(checkerName=[checker_id_filter])

                run_results = self._cc_client.getRunResults([runid],
                                                            500,
                                                            0,
                                                            sort_types,
                                                            cid_f,
                                                            None)
                for r in run_results:
                    print(r)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_filter_file_path(self):
        """ Filter by checker id. """
        runid = self._runids[0]

        severity_test_data = self._testproject_data[self._clang_to_test][
            'filter_filepath']

        for level in severity_test_data:
            for filepath_filter, test_result_count in level.items():
                logging.debug('File path filter ' + filepath_filter +
                              ' test result count: ' + str(test_result_count))

                sort_types = None
                fp_f = ReportFilter(filepath=[filepath_filter])

                run_result_count = self._cc_client.getRunResultCount(
                    [runid], fp_f, None)
                run_results = self._cc_client.getRunResults([runid],
                                                            run_result_count,
                                                            0,
                                                            sort_types,
                                                            fp_f,
                                                            None)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_filter_case_insensitive_file_path(self):
        """ Filter by file path case insensitive."""

        runid = self._runids[0]
        filter_test_data = self._testproject_data[self._clang_to_test][
            'filter_filepath_case_insensitive']

        for level in filter_test_data:
            for filepath_filter, test_result_count in level.items():
                logging.debug('File path filter ' + filepath_filter +
                              ' test result count: ' + str(test_result_count))

                sort_types = None
                fp_f = ReportFilter(filepath=[filepath_filter])

                run_result_count = self._cc_client.getRunResultCount(
                    [runid], fp_f, None)
                run_results = self._cc_client.getRunResults([runid],
                                                            run_result_count,
                                                            0,
                                                            sort_types,
                                                            fp_f,
                                                            None)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_run1_run2_all_results(self):
        """
            Get all the results for run1 and run2.
            Without any filtering.
        """

        run_result_count = self._cc_client.getRunResultCount(self._runids,
                                                             None,
                                                             None)

        self.assertEqual(run_result_count, 65)

        run_results = self._cc_client.getRunResults(self._runids,
                                                    run_result_count,
                                                    0,
                                                    [],
                                                    None,
                                                    None)

        self.assertIsNotNone(run_results)
        self.assertEqual(run_result_count, len(run_results))

    def test_filter_review_status(self):
        """ Filter by review status. """
        runid = self._runids[0]

        severity_test_data = self._testproject_data[self._clang_to_test][
            'filter_review_status']

        run_result_count = self._cc_client.getRunResultCount([runid],
                                                             None,
                                                             None)
        run_results = self._cc_client.getRunResults([runid],
                                                    run_result_count,
                                                    0,
                                                    [],
                                                    None,
                                                    None)

        report_ids = [r.reportId for r in run_results]

        # Set all review statuses in case some other tests changed them.
        for rid in report_ids:
            self._cc_client.changeReviewStatus(rid,
                                               ReviewStatus.CONFIRMED,
                                               '')

        for level in severity_test_data:
            for review_status, test_result_count in level.items():
                logging.debug('Review status ' + review_status +
                              ' test result count: ' + str(test_result_count))
                sort_types = None
                status = get_status(review_status)
                s_f = ReportFilter(reviewStatus=[status])

                run_result_count = self._cc_client.getRunResultCount(
                    [runid], s_f, None)

                run_results = self._cc_client.getRunResults([runid],
                                                            run_result_count,
                                                            0,
                                                            sort_types,
                                                            s_f,
                                                            None)

                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_filter_unique(self):
        """
         Get all results by unique and non unique filter and check the results.
        """

        sort_types = None
        simple_filter = ReportFilter()
        unique_filter = ReportFilter(isUnique=True)

        # Get unique results.
        run_results = self._cc_client.getRunResults(
            None, 500, 0, sort_types, unique_filter, None)
        unique_result_count = self._cc_client.getRunResultCount(
            None, unique_filter, None)
        unique_bughash = set([res.bugHash for res in run_results])

        # Get simple results.
        run_results = self._cc_client.getRunResults(
            None, 500, 0, sort_types, simple_filter, None)
        simple_result_count = self._cc_client.getRunResultCount(
            None, simple_filter, None)
        simple_bughash = set([res.bugHash for res in run_results])

        diff_hashes = list(simple_bughash.difference(unique_bughash))
        self.assertEqual(0, len(diff_hashes))
        self.assertGreaterEqual(simple_result_count, unique_result_count)

    def test_uniqueing_compared_to_test_config(self):
        """
         In the test config there are all of the reports without
        uniqueing. This test checks if the uniqueing works for the
        getRunResultCount api call.
        """
        runid = self._runids[0]

        bugs = self._testproject_data[self._clang_to_test]['bugs']

        unique_filter = ReportFilter(isUnique=True)
        run_result_count = self._cc_client.getRunResultCount([runid],
                                                             unique_filter,
                                                             None)

        unique_bugs = set()
        # Uniqueing is done based on bug hash.
        for b in bugs:
            unique_bugs.add((b['hash']))

        self.assertEqual(len(unique_bugs), run_result_count)
