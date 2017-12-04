#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import base64
import logging
import os
import unittest

from libtest import env

from codeCheckerDBAccess_v6.ttypes import Encoding
from codeCheckerDBAccess_v6.ttypes import LinesInFilesRequested
from codeCheckerDBAccess_v6.ttypes import ReportFilter


class TestGetLinesInFile(unittest.TestCase):

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
        self._project_info = env.setup_test_proj_cfg(test_workspace)

    def __get_file_id_for_path(self, run_id, file_path):
        # Returns file id for the given file path in the given run.
        file_filter = ReportFilter(filepath=[file_path])
        run_results = self._cc_client.getRunResults(
            [run_id], 1, 0, None, file_filter, None)

        self.assertTrue(len(run_results))
        return run_results[0].fileId

    def __check_lines_in_source_file_contents(self, lines_in_files_requested,
                                              encoding, expected):
        """
        Get line content information with the given encoding and check the
        results.
        """
        file_to_lines_map = self._cc_client.getLinesInSourceFileContents(
            lines_in_files_requested, encoding)
        for file_id in expected:
            for line in expected[file_id]:
                source_line = file_to_lines_map[file_id][line]
                if encoding == Encoding.BASE64:
                    source_line = base64.b64decode(source_line)

                self.assertEqual(source_line,
                                 expected[file_id][line])

    def __get_local_lines_in_source_file_contents(self, file_name, lines):
        """
        :param file_name File name under the project path.
        :param lines Line number starting from 1.
        Returns line content information for the given file located in the
        project path.
        """
        file_path = os.path.join(self._project_info['project_path'], file_name)
        with open(file_path, 'r') as f:
            lines_in_file = f.read().split('\n')
            return {line: '' if len(lines_in_file) < line else
                    lines_in_file[line - 1] for line in lines}

    def test_get_lines_in_source_file_contents(self):
        """
        Get line content information for multiple files in different positions.
        """
        runid = self._runid
        logging.debug('Get line content information from the db for runid: ' +
                      str(runid))

        # Get reports by file to get a file id.
        file_id_1 = self.__get_file_id_for_path(runid, "*call_and_message.cpp")
        file_id_2 = self.__get_file_id_for_path(runid, "*divide_zero.cpp")

        lines_in_files_requested = [
            LinesInFilesRequested(fileId=file_id_1, lines=[15, 20]),
            LinesInFilesRequested(fileId=file_id_2, lines=[12, 19])]

        expected = {
            file_id_1: self.__get_local_lines_in_source_file_contents(
                'call_and_message.cpp', [15, 20]),
            file_id_2: self.__get_local_lines_in_source_file_contents(
                'divide_zero.cpp', [12, 19])
        }

        # Check results by using default encoding.
        self.__check_lines_in_source_file_contents(lines_in_files_requested,
                                                   Encoding.DEFAULT,
                                                   expected)

        # Check results by using base64 encoding.
        self.__check_lines_in_source_file_contents(lines_in_files_requested,
                                                   Encoding.BASE64,
                                                   expected)
