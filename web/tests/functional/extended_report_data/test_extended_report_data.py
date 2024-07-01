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
import shutil
import sys
import unittest

from libtest import codechecker
from libtest import env
from libtest import project

from codechecker_api.codeCheckerDBAccess_v6.ttypes import ReportFilter, \
    RunFilter, ExtendedReportDataType


class TestExtendedReportData(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing detection_status."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('extended_report_data')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_env = env.test_env(TEST_WORKSPACE)

        # Configuration options.
        codechecker_cfg = {
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'run_names': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'extended_report_data'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Copy test projects and replace file path in plist files.
        test_projects = ['notes', 'macros']
        for test_project in test_projects:
            test_project_path = os.path.join(TEST_WORKSPACE, "test_proj",
                                             test_project)
            shutil.copytree(project.path(test_project), test_project_path)

            for test_file in os.listdir(test_project_path):
                if test_file.endswith(".plist"):
                    test_file_path = os.path.join(test_project_path, test_file)
                    with open(test_file_path, 'r+',
                              encoding="utf-8", errors="ignore") as plist_file:
                        content = plist_file.read()
                        new_content = content.replace("$FILE_PATH$",
                                                      test_project_path)
                        plist_file.seek(0)
                        plist_file.truncate()
                        plist_file.write(new_content)

            codechecker_cfg['reportdir'] = test_project_path

            ret = codechecker.store(codechecker_cfg, test_project)
            if ret:
                sys.exit(1)
            print("Analyzing test project was succcessful.")

            codechecker_cfg['run_names'].append(test_project)

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE,
                            {'codechecker_cfg': codechecker_cfg})

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

        return self._cc_client.getRunResults(
            [run_id], None, 0, [], ReportFilter(), None, False)

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
