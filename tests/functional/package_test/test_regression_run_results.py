#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import logging
import os
import re
import unittest

from codeCheckerDBAccess.ttypes import Order
from codeCheckerDBAccess.ttypes import ReportFilter
from codeCheckerDBAccess.ttypes import SortMode
from codeCheckerDBAccess.ttypes import SortType
from test_utils.debug_printer import print_run_results
from test_utils.thrift_client_to_db import CCViewerHelper


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

    def test_get_run_results_no_filter(self):
        """ Get the run results without filtering just the
            result count is checked. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_result_count = self._cc_client.getRunResultCount(runid, [])
        self.assertTrue(run_result_count)

        run_results = self._cc_client.getRunResults(runid, run_result_count,
                                                    0, [], [])
        self.assertIsNotNone(run_results)

        print_run_results(run_results)

        self.assertEqual(run_result_count, len(run_results))

    def test_get_run_results_checker_id_and_file_path(self):
        """ Get all the run results and compare with the results
            in the project config. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_result_count = self._cc_client.getRunResultCount(runid, [])
        self.assertTrue(run_result_count)

        run_results = self._cc_client.getRunResults(runid, run_result_count,
                                                    0, [], [])
        self.assertIsNotNone(run_results)

        print_run_results(run_results)

        self.assertEqual(run_result_count, len(run_results))

        found_all = True
        not_found = []
        for bug in self._testproject_data['bugs']:
            found = False
            for run_res in run_results:
                found |= ((run_res.checkedFile.endswith(bug['file'])) and
                          (run_res.lastBugPosition.startLine == bug['line']) and
                          (run_res.checkerId == bug['checker']) and
                          (run_res.bugHash == bug['hash']))
            found_all &= found
            if not found:
                not_found.append(bug)

        print('Not found bugs:')
        for bug in not_found:
            print(bug)

        self.assertTrue(found_all)

    def test_get_source_file_content(self):  # also for testing Unicode support
        """ Get the stored source file content from the database and compare
            it with the original version, unicode encoding decoding is tested
            during the storage and retrieving the data. """
        runid = self._runid
        simple_filters = [ReportFilter(checkerId='*', filepath='*.c*')]

        run_result_count = self._cc_client.getRunResultCount(runid,
                                                             simple_filters)
        self.assertTrue(run_result_count)

        run_results = self._cc_client.getRunResults(runid, run_result_count,
                                                    0, [], simple_filters)
        self.assertIsNotNone(run_results)

        for run_res in run_results:
            self.assertTrue(re.match(r'.*\.c(pp)?$', run_res.checkedFile))

            logging.debug('Getting the content of ' + run_res.checkedFile)

            file_data = self._cc_client.getSourceFileData(run_res.fileId, True)
            self.assertIsNotNone(file_data)

            file_content1 = file_data.fileContent
            self.assertIsNotNone(file_content1)

            with open(run_res.checkedFile) as source_file:
                file_content2 = source_file.read()

            self.assertEqual(file_content1, file_content2)

        logging.debug('got ' + str(len(run_results)) + ' files')

        self.assertEqual(run_result_count, len(run_results))

    def test_zzzzz_get_run_results_checker_msg_filter_suppressed(self):
        """ This test must run for the last, suppresses some results
            that could cause some other tests to fail which depend
            on the result count. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        simple_filters = [ReportFilter(suppressed=False)]
        run_results = self._cc_client.getRunResults(runid, 50, 0, [],
                                                    simple_filters)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        suppress_msg = r'My beautiful Unicode comment.'
        bug = run_results[0]
        success = self._cc_client.suppressBug([runid],
                                              bug.reportId,
                                              suppress_msg)
        self.assertTrue(success)
        logging.debug('Bug suppressed successfully')

        simple_filters = [ReportFilter(suppressed=True)]
        run_results = self._cc_client.getRunResults(runid, 50, 0, [],
                                                    simple_filters)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        filtered_run_results = filter(
            lambda result:
            (result.reportId == bug.reportId) and result.suppressed,
            run_results)
        self.assertEqual(len(filtered_run_results), 1)
        suppressed_bug = filtered_run_results[0]
        self.assertEqual(suppressed_bug.suppressComment, suppress_msg)

        success = self._cc_client.unSuppressBug([runid],
                                                suppressed_bug.reportId)
        self.assertTrue(success)
        logging.debug('Bug unsuppressed successfully')

        simple_filters = [ReportFilter(suppressed=False)]
        run_results = self._cc_client.getRunResults(runid, 50, 0, [],
                                                    simple_filters)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        filtered_run_results = filter(
            lambda result:
            (result.reportId == bug.reportId) and not result.suppressed,
            run_results)
        self.assertEqual(len(filtered_run_results), 1)

        logging.debug('Done.\n')

    def test_get_run_results_severity_sort(self):
        """ Get the results and sort them by severity and filename. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))
        sort_mode1 = SortMode(SortType.SEVERITY, Order.ASC)
        sort_mode2 = SortMode(SortType.FILENAME, Order.ASC)
        sort_types = [sort_mode1, sort_mode2]

        run_result_count = self._cc_client.getRunResultCount(runid, [])
        self.assertTrue(run_result_count)

        run_results = self._cc_client.getRunResults(runid, run_result_count,
                                                    0, sort_types, [])
        self.assertIsNotNone(run_results)

        for i in range(run_result_count - 1):
            bug1 = run_results[i]
            bug2 = run_results[i + 1]
            self.assertTrue(bug1.severity <= bug2.severity)
            self.assertTrue((bug1.severity != bug2.severity) or
                            (bug1.checkedFile <= bug2.checkedFile))

        print_run_results(run_results)

        self.assertEqual(run_result_count, len(run_results))

    def test_get_run_results_sorted2(self):
        """ Get the results and sort them by filename and checkername. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))
        sortMode1 = SortMode(SortType.FILENAME, Order.ASC)
        sortMode2 = SortMode(SortType.CHECKER_NAME, Order.ASC)
        sort_types = [sortMode1, sortMode2]

        run_result_count = self._cc_client.getRunResultCount(runid, [])
        self.assertTrue(run_result_count)

        run_results = self._cc_client.getRunResults(runid, run_result_count, 0,
                                                    sort_types, [])
        self.assertIsNotNone(run_results)

        print_run_results(run_results)

        self.assertEqual(run_result_count, len(run_results))

        for i in range(run_result_count - 1):
            bug1 = run_results[i]
            bug2 = run_results[i + 1]
            self.assertTrue(bug1.checkedFile <= bug2.checkedFile)
            self.assertTrue((bug1.checkedFile != bug2.checkedFile) or
                            (bug1.lastBugPosition.startLine <=
                             bug2.lastBugPosition.startLine) or
                            (bug1.checkerId <= bug2.checkerId))
