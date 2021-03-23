#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test database cleanup.
"""


import json
import multiprocessing
import os
import unittest
from shutil import copyfile, rmtree

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentData, \
    ReportFilter, ReviewStatus, RunFilter, Severity

from libtest import codechecker
from libtest import env


class TestDbCleanup(unittest.TestCase):

    def setUp(self):
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self.codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        self.test_dir = os.path.join(self.test_workspace, 'test_files')

        try:
            os.makedirs(self.test_dir)
        except os.error:
            # Directory already exists.
            pass

        cc_package = env.codechecker_package()
        original_severity_cfg = os.path.join(cc_package,
                                             'config',
                                             'checker_severity_map.json')

        self.workspace_severity_cfg = os.path.join(self.test_workspace,
                                                   'checker_severity_map.json')
        copyfile(original_severity_cfg, self.workspace_severity_cfg)

        self.codechecker_cfg['check_env']['CC_SEVERITY_MAP_FILE'] = \
            self.workspace_severity_cfg

    def __create_test_dir(self):
        makefile = "all:\n\t$(CXX) -c a/main.cpp -o /dev/null\n"
        project_info = {
            "name": "hello",
            "clean_cmd": "",
            "build_cmd": "make"
        }
        source_main = """
// Test file for db_cleanup
#include "f.h"
int main() { f(0); }
"""
        source_f = """
// Test file for db_cleanup
int f(int x) { return 1 / x; }
"""

        os.makedirs(os.path.join(self.test_dir, 'a'))

        with open(os.path.join(self.test_dir, 'Makefile'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(makefile)
        with open(os.path.join(self.test_dir, 'project_info.json'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            json.dump(project_info, f)
        with open(os.path.join(self.test_dir, 'a', 'main.cpp'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(source_main)
        with open(os.path.join(self.test_dir, 'a', 'f.h'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(source_f)

    def __rename_project_dir(self):
        os.rename(os.path.join(self.test_dir, 'a'),
                  os.path.join(self.test_dir, 'b'))

        makefile = "all:\n\t$(CXX) -c b/main.cpp -o /dev/null\n"

        with open(os.path.join(self.test_dir, 'Makefile'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(makefile)

    def __get_run_id(self, run_name):
        """ Get run id based on the given run name. """
        run_filter = RunFilter()
        run_filter.names = [run_name]
        run_filter.exactMatch = True

        runs = self._cc_client.getRunData(run_filter, None, 0, None)
        return runs[0].runId

    def __get_files_in_report(self, run_name):
        codechecker.check_and_store(self.codechecker_cfg,
                                    run_name,
                                    self.test_dir)

        run_id = self.__get_run_id([run_name])

        reports \
            = self._cc_client.getRunResults([run_id], 10, 0, [], None, None,
                                            False)

        details = self._cc_client.getReportDetails(reports[0].reportId)

        files = set()
        files.update([bp.fileId for bp in details.pathEvents])
        files.update([bp.fileId for bp in details.executionPath])

        file_ids = set()
        for file_id in files:
            file_data = self._cc_client.getSourceFileData(file_id, False, None)
            if file_data.fileId is not None:
                file_ids.add(file_data.fileId)

        return file_ids

    def __check_serverity_of_reports(self, run_name):
        """
        This will check whether reports in the database has the same severity
        levels as in the severity map config file.
        """
        run_filter = RunFilter()
        run_filter.names = [run_name]
        run_filter.exactMatch = True

        runs = self._cc_client.getRunData(run_filter, None, 0, None)
        run_id = runs[0].runId

        reports \
            = self._cc_client.getRunResults([run_id], 10, 0, [], None, None,
                                            False)

        with open(self.workspace_severity_cfg, 'r',
                  encoding="utf-8", errors="ignore") as severity_cgf_file:
            severity_map = json.load(severity_cgf_file)
            for report in reports:
                severity_id = severity_map.get(report.checkerId, 'UNSPECIFIED')
                self.assertEqual(Severity._VALUES_TO_NAMES[report.severity],
                                 severity_id)

    def test_garbage_file_collection(self):
        event = multiprocessing.Event()
        event.clear()

        self.codechecker_cfg['viewer_port'] = env.get_free_port()
        env.export_test_cfg(self.test_workspace,
                            {'codechecker_cfg': self.codechecker_cfg})

        env.enable_auth(self.test_workspace)

        server_access = codechecker.start_server(self.codechecker_cfg, event)
        server_access['viewer_port'] \
            = self.codechecker_cfg['viewer_port']
        server_access['viewer_product'] \
            = self.codechecker_cfg['viewer_product']

        codechecker.add_test_package_product(server_access,
                                             self.test_workspace)

        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        run_name1 = 'db_cleanup_test'
        run_name2 = f'{run_name1}2'

        self.__create_test_dir()

        # Store the results.
        codechecker.check_and_store(self.codechecker_cfg, run_name1,
                                    self.test_dir)

        # Store the results to a different run too to see if we remove only one
        # run, comments and review statuses not cleared.
        codechecker.check_and_store(self.codechecker_cfg, run_name2,
                                    self.test_dir)

        run_id1 = self.__get_run_id([run_name1])
        report = self._cc_client.getRunResults(None, 1, 0, [], None,
                                               None, False)[0]

        report_hash = report.bugHash
        report_id = report.reportId

        # Add a new comment.
        comment = CommentData(author='anybody', message='Msg')
        success = self._cc_client.addComment(report_id, comment)
        self.assertTrue(success)

        # Change review status.
        success = self._cc_client.changeReviewStatus(
            report_id, ReviewStatus.CONFIRMED, 'Real bug')
        self.assertTrue(success)

        # Remove the first storage.
        self._cc_client.removeRun(run_id1, None)

        # Comments and review statuses are not cleared, because the second
        # run results still reference them.
        run_id2 = self.__get_run_id([run_name2])
        r_filter = ReportFilter(reviewStatus=[ReviewStatus.CONFIRMED])
        run_results = self._cc_client.getRunResults([run_id2], 1, 0,
                                                    None, r_filter, None,
                                                    False)
        self.assertTrue(run_results)

        comments = self._cc_client.getComments(run_results[0].reportId)
        self.assertTrue(comments)

        # Remove the second run too, so it will cleanup the unused commments
        # and review statuses.
        self._cc_client.removeRun(run_id2, None)

        # Store results again and check that previous comments and review
        # statuses are gone.
        files_in_report_before = self.__get_files_in_report(run_name1)

        r_filter = ReportFilter(reportHash=[report_hash])
        report = self._cc_client.getRunResults(None, 1, 0, None, r_filter,
                                               None, False)[0]
        report_id = report.reportId

        comments = self._cc_client.getComments(report_id)
        self.assertFalse(comments)

        r_filter = ReportFilter(reviewStatus=[ReviewStatus.CONFIRMED])
        run_results = self._cc_client.getRunResults(None, 1, 0, None, r_filter,
                                                    None, False)
        self.assertFalse(run_results)

        # Checker severity levels.
        self.__check_serverity_of_reports(run_name1)

        self.__rename_project_dir()

        # Delete previous analysis report directory.
        rmtree(self.codechecker_cfg['reportdir'])

        files_in_report_after = self.__get_files_in_report(run_name1)

        event.set()

        event.clear()

        # Change severity level of core.DivideZero to LOW.
        with open(self.workspace_severity_cfg, 'r+',
                  encoding='utf-8', errors='ignore') as severity_cgf_file:
            severity_map = json.load(severity_cgf_file)
            severity_map['core.DivideZero'] = 'LOW'

            severity_cgf_file.seek(0)
            severity_cgf_file.truncate()
            severity_cgf_file.write(str(json.dumps(severity_map)))

        self.codechecker_cfg['viewer_port'] = env.get_free_port()
        env.export_test_cfg(self.test_workspace,
                            {'codechecker_cfg': self.codechecker_cfg})

        codechecker.start_server(self.codechecker_cfg,
                                 event)
        codechecker.login(self.codechecker_cfg,
                          self.test_workspace,
                          'cc',
                          'test')

        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        self.assertEqual(len(files_in_report_before & files_in_report_after),
                         0)

        for file_id in files_in_report_before:
            f = self._cc_client.getSourceFileData(file_id, False, None)
            self.assertIsNone(f.fileId)

        # Checker severity levels.
        self.__check_serverity_of_reports(run_name1)

        event.set()
