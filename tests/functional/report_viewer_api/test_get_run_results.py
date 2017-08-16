#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import base64
import logging
import os
import re
import unittest

from codeCheckerDBAccess.ttypes import Encoding
from codeCheckerDBAccess.ttypes import Order
from codeCheckerDBAccess.ttypes import ReportFilter
from codeCheckerDBAccess.ttypes import SortMode
from codeCheckerDBAccess.ttypes import SortType

from libtest.debug_printer import print_run_results
from libtest.thrift_client_to_db import get_all_run_results
from libtest.result_compare import find_all
from libtest import env


class RunResults(unittest.TestCase):

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

        self._runid = test_runs[0].runId

    def test_get_run_results_no_filter(self):
        """ Get all the run results without any filtering. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_result_count = self._cc_client.getRunResultCount([runid], [])
        self.assertTrue(run_result_count)

        run_results = get_all_run_results(self._cc_client, runid)

        print_run_results(run_results)

        self.assertIsNotNone(run_results)
        self.assertEqual(run_result_count, len(run_results))

    def test_get_run_results_checker_id_and_file_path(self):
        """ Test if all the bugs are found based
            on the test project configuration. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_result_count = self._cc_client.getRunResultCount([runid], [])
        self.assertTrue(run_result_count)

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)
        self.assertEqual(run_result_count, len(run_results))

        test_project_results = self._testproject_data[
            self._clang_to_test]['bugs']
        for r in test_project_results:
            print(r)

        not_found = find_all(run_results, test_project_results)

        print_run_results(run_results)

        if not_found:
            print("===================")
            print('Not found bugs:')
            for bug in not_found:
                print(bug)
            print("===================")

        self.assertEqual(len(not_found), 0)

    def test_get_source_file_content(self):
        """
        Test getting the source file content stored to the database.
        Test unicode support the stored file can be decoded properly
        compare results form the database to the original file.
        """

        runid = self._runid
        simple_filters = [ReportFilter(checkerId='*', filepath='*.c*')]

        run_result_count = self._cc_client.getRunResultCount([runid],
                                                             simple_filters)
        self.assertTrue(run_result_count)

        run_results = get_all_run_results(self._cc_client,
                                          runid,
                                          filters=simple_filters)
        self.assertIsNotNone(run_results)

        for run_res in run_results:
            self.assertTrue(re.match(r'.*\.c(pp)?$', run_res.checkedFile))

            logging.debug('Getting the content of ' + run_res.checkedFile)

            file_data = self._cc_client.getSourceFileData(run_res.fileId,
                                                          True,
                                                          None)
            self.assertIsNotNone(file_data)

            file_content1 = file_data.fileContent
            self.assertIsNotNone(file_content1)

            with open(run_res.checkedFile) as source_file:
                file_content2 = source_file.read()

            self.assertEqual(file_content1, file_content2)

            file_data_b64 = self._cc_client.getSourceFileData(
                run_res.fileId, True, Encoding.BASE64)
            self.assertIsNotNone(file_data_b64)

            file_content1_b64 = base64.b64decode(file_data_b64.fileContent)
            self.assertIsNotNone(file_content1_b64)

            self.assertEqual(file_content1_b64, file_content2)

        logging.debug('got ' + str(len(run_results)) + ' files')

        self.assertEqual(run_result_count, len(run_results))

    def test_get_run_results_severity_sort(self):
        """ Get the run results and sort them by severity and filename ASC. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))
        sort_mode1 = SortMode(SortType.SEVERITY, Order.ASC)
        sort_mode2 = SortMode(SortType.FILENAME, Order.ASC)
        sort_types = [sort_mode1, sort_mode2]

        run_result_count = self._cc_client.getRunResultCount([runid], [])
        self.assertTrue(run_result_count)

        run_results = get_all_run_results(self._cc_client,
                                          runid,
                                          sort_types,
                                          [])
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
        """ Get the run results and sort them by file name and
            checker name ASC. """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))
        sortMode1 = SortMode(SortType.FILENAME, Order.ASC)
        sortMode2 = SortMode(SortType.CHECKER_NAME, Order.ASC)
        sort_types = [sortMode1, sortMode2]

        run_result_count = self._cc_client.getRunResultCount([runid], [])
        self.assertTrue(run_result_count)

        run_results = get_all_run_results(self._cc_client,
                                          runid,
                                          sort_types,
                                          [])
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
