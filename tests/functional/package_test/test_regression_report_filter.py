#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
import traceback
import unittest

from codeCheckerDBAccess.ttypes import ReportFilter

import shared

from test_utils.thrift_client_to_db import CCViewerHelper


def get_severity_level(name):
    """ Convert serverity name to value. """
    return shared.ttypes.Severity._NAMES_TO_VALUES[name]


class RunResults(unittest.TestCase):

    _ccClient = None

    # selected runid for running the tests
    _runid = None

    def _select_one_runid(self):
        runs = self._cc_client.getRunData()
        self.assertIsNotNone(runs)
        self.assertNotEqual(len(runs), 0)
        # select one random run
        idx = 0
        return runs[idx].runId

    def setUp(self):
        host = 'localhost'
        port = int(os.environ['CC_TEST_VIEWER_PORT'])
        uri = '/'
        self._testproject_data = json.loads(os.environ['CC_TEST_PROJECT_INFO'])
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = CCViewerHelper(host, port, uri)
        self._runid = self._select_one_runid()

    def test_filter_none(self):
        ''' Filter value is None should return all results'''
        runid = self._runid
        sort_types = None
        simple_filters = None

        run_result_count = self._cc_client.getRunResultCount(runid,
                                                             simple_filters)
        self.assertIsNotNone(run_result_count)

        run_results = self._cc_client.getRunResults(runid, run_result_count, 0,
                                                    sort_types, simple_filters)
        self.assertIsNotNone(run_results)
        self.assertEqual(run_result_count, len(run_results))

    def test_filter_empty(self):
        ''' Filter value is empty list should return all results'''
        runid = self._runid
        sort_types = None
        simple_filters = []

        run_result_count = self._cc_client.getRunResultCount(runid,
                                                             simple_filters)
        self.assertIsNotNone(run_result_count)

        run_results = self._cc_client.getRunResults(runid, run_result_count, 0,
                                                    sort_types, simple_filters)
        self.assertIsNotNone(run_results)
        self.assertEqual(run_result_count, len(run_results))

    def test_filter_severity(self):
        ''' Filter by severity levels'''
        runid = self._runid

        severity_test_data = self._testproject_data['filter_severity_levels']

        for level in severity_test_data:
            for severity_level, test_result_count in level.iteritems():
                logging.debug('Severity level filter ' + severity_level +
                              ' test result count: ' + str(test_result_count))
                sort_types = None
                simple_filters = []
                sev = get_severity_level(severity_level)
                simple_filter = ReportFilter(severity=sev)
                simple_filters.append(simple_filter)

                run_result_count = self._cc_client.getRunResultCount(
                    runid, simple_filters)
                run_results = self._cc_client.getRunResults(
                    runid, run_result_count, 0, sort_types, simple_filters)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_filter_checker_id(self):
        ''' Filter by checker id'''
        runid = self._runid

        severity_test_data = self._testproject_data['filter_checker_id']

        for level in severity_test_data:
            for checker_id_filter, test_result_count in level.iteritems():
                logging.debug('Checker id filter ' + checker_id_filter +
                              ' test result count: ' + str(test_result_count))
                sort_types = None
                simple_filters = []
                simple_filter = ReportFilter(checkerId=checker_id_filter)
                simple_filters.append(simple_filter)

                run_result_count = self._cc_client.getRunResultCount(
                    runid, simple_filters)
                run_results = self._cc_client.getRunResults(
                    runid, run_result_count, 0, sort_types, simple_filters)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_filter_file_path(self):
        ''' Filter by checker id'''
        runid = self._runid

        severity_test_data = self._testproject_data['filter_filepath']

        for level in severity_test_data:
            for filepath_filter, test_result_count in level.iteritems():
                logging.debug('File path filter ' + filepath_filter +
                     ' test result count: ' + str(test_result_count))

                sort_types = None
                simple_filters = []
                simple_filter = ReportFilter(filepath=filepath_filter)
                simple_filters.append(simple_filter)

                run_result_count = self._cc_client.getRunResultCount(
                    runid, simple_filters)
                run_results = self._cc_client.getRunResults(
                    runid, run_result_count, 0, sort_types, simple_filters)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))

    def test_filter_case_insensitive_file_path(self):
        ''' Filter by file path case insensitive'''

        runid = self._runid
        filter_test_data = self._testproject_data['filter_filepath_case_insensitive']

        for level in filter_test_data:
            for filepath_filter, test_result_count in level.iteritems():
                logging.debug('File path filter ' + filepath_filter +
                     ' test result count: ' + str(test_result_count))

                sort_types = None
                simple_filters = []
                simple_filter = ReportFilter(filepath=filepath_filter)
                simple_filters.append(simple_filter)

                run_result_count = self._cc_client.getRunResultCount(
                    runid, simple_filters)
                run_results = self._cc_client.getRunResults(
                    runid, run_result_count, 0, sort_types, simple_filters)
                self.assertIsNotNone(run_results)
                self.assertEqual(test_result_count, len(run_results))
