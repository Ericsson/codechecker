#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
""" detection_status function test. """
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

from codeCheckerDBAccess_v6.ttypes import *

from libtest import codechecker
from libtest import env


class TestDetectionStatus(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        self.src_dir = os.path.dirname(__file__)
        self.test_files_dir = os.path.join(self.src_dir, 'test_files')
        self.analyzer_reports_dir = os.path.join(self.test_files_dir,
                                                 'analyzer_reports')
        self.source_files_dir = os.path.join(self.test_files_dir,
                                             'source_files')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

    def store(self, reports_dir, test_files_dir):
        """ Store the given version of analyzer reports to the server. """
        print("Storing analyzer reports: " + reports_dir)
        test_files_data = codechecker.add_analyzer_reports(reports_dir,
                                                           self.test_workspace,
                                                           test_files_dir)

        self._codechecker_cfg['reportdir'] = \
            test_files_data['analyzer_reports_dir']

        project_name = 'hello'
        codechecker.store(self._codechecker_cfg, project_name)

    def test_same_file_change(self):
        """
        This tests the change of the detection status of bugs when the file
        content changes.
        """
        runs = self._cc_client.getRunData(None)

        if runs:
            run_id = max(map(lambda run: run.runId, runs))
            self._cc_client.removeRun(run_id)

        reports_dir = os.path.join(self.analyzer_reports_dir, 'v1')
        test_files_dir = os.path.join(self.source_files_dir, 'v1')
        self.store(reports_dir, test_files_dir)

        runs = self._cc_client.getRunData(None)
        run_id = max(map(lambda run: run.runId, runs))

        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)

        self.assertEqual(len(reports), 5)
        self.assertTrue(all(map(
            lambda r: r.detectionStatus == DetectionStatus.NEW,
            reports)))

        reports_dir = os.path.join(self.analyzer_reports_dir, 'v2', 'simple')
        test_files_dir = os.path.join(self.source_files_dir, 'v2')
        self.store(reports_dir, test_files_dir)

        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)
        for report in reports:
            if report.detectionStatus == DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['3cfc9ec31117e138b052abfb064517e5',
                               '209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])
            elif report.detectionStatus == DetectionStatus.NEW:
                self.assertIn(report.bugHash,
                              ['cbd629ba2ee25c41cdbf5e2e336b1b1c'])
            else:
                self.assertTrue(False)

        reports_dir = os.path.join(self.analyzer_reports_dir, 'v3')
        test_files_dir = os.path.join(self.source_files_dir, 'v3')
        self.store(reports_dir, test_files_dir)

        # Check the third file version
        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)
        for report in reports:
            if report.detectionStatus == DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])

                file_content = self._cc_client.getSourceFileData(
                    report.fileId,
                    True,
                    Encoding.DEFAULT).fileContent

                source_file_path = os.path.join(self.source_files_dir, 'v2',
                                                'main.cpp')
                with open(source_file_path) as source_file:
                    self.assertEqual(
                        file_content,
                        source_file.read(),
                        "Resolved bugs should be shown with the old file "
                        "content.")

            elif report.detectionStatus == DetectionStatus.NEW:
                self.assertIn(report.bugHash,
                              ['ac147b31a745d91be093bd70bbc5567c'])
            elif report.detectionStatus == DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['3cfc9ec31117e138b052abfb064517e5',
                               'cbd629ba2ee25c41cdbf5e2e336b1b1c'])

                file_content = self._cc_client.getSourceFileData(
                    report.fileId,
                    True,
                    Encoding.DEFAULT).fileContent

                source_file_path = os.path.join(self.source_files_dir, 'v3',
                                                'main.cpp')
                with open(source_file_path) as source_file:
                    self.assertEqual(
                        file_content,
                        source_file.read(),
                        "Unresolved bug should be shown with the new file "
                        "content.")

            else:
                self.assertTrue(False)

        # Check the second file version again
        reports_dir = os.path.join(self.analyzer_reports_dir, 'v2', 'simple')
        test_files_dir = os.path.join(self.source_files_dir, 'v2')
        self.store(reports_dir, test_files_dir)

        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)
        for report in reports:
            if report.detectionStatus == DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['3cfc9ec31117e138b052abfb064517e5',
                               'cbd629ba2ee25c41cdbf5e2e336b1b1c'])
            elif report.detectionStatus == DetectionStatus.REOPENED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])
            elif report.detectionStatus == DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['ac147b31a745d91be093bd70bbc5567c'])

        # Check the fourth file version
        reports_dir = os.path.join(self.analyzer_reports_dir, 'v4')
        test_files_dir = os.path.join(self.source_files_dir, 'v4')
        self.store(reports_dir, test_files_dir)

        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)
        for report in reports:
            if report.detectionStatus == DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba',
                               'cbd629ba2ee25c41cdbf5e2e336b1b1c',
                               '3cfc9ec31117e138b052abfb064517e5'])

                file_content = self._cc_client.getSourceFileData(
                    report.fileId,
                    True,
                    Encoding.DEFAULT).fileContent

                source_file_path = os.path.join(self.source_files_dir, 'v4',
                                                'main.cpp')
                with open(source_file_path) as source_file:
                    self.assertEqual(
                        file_content,
                        source_file.read(),
                        "Reopened bugs should be shown with the new file "
                        "content.")

            elif report.detectionStatus == DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['ac147b31a745d91be093bd70bbc5567c'])

    def test_check_without_metadata(self):
        """
        This test checks whether the storage works without a metadata.json.
        """
        runs = self._cc_client.getRunData(None)
        if runs:
            run_id = max(map(lambda run: run.runId, runs))

            # Remove the run.
            self._cc_client.removeRun(run_id)

        reports_dir = os.path.join(self.analyzer_reports_dir, 'v1')
        test_files_dir = os.path.join(self.source_files_dir, 'v1')
        self.store(reports_dir, test_files_dir)

        runs = self._cc_client.getRunData(None)
        run_id = max(map(lambda run: run.runId, runs))

        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)

        self.assertEqual(len(reports), 5)

    def test_detection_status_off(self):
        """
        This test checks reports which have detection status of 'Off'.
        """
        runs = self._cc_client.getRunData(None)
        if runs:
            run_id = max(map(lambda run: run.runId, runs))

            # Remove the run.
            self._cc_client.removeRun(run_id)

        cfg = dict(self._codechecker_cfg)

        reports_dir = os.path.join(self.analyzer_reports_dir, 'v1')
        test_files_dir = os.path.join(self.source_files_dir, 'v1')
        self.store(reports_dir, test_files_dir)

        reports_dir = os.path.join(self.analyzer_reports_dir, 'v2', 'simple')
        test_files_dir = os.path.join(self.source_files_dir, 'v2')
        self.store(reports_dir, test_files_dir)

        reports = self._cc_client.getRunResults(None,
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)
        offed_reports = [r for r in reports
                         if r.detectionStatus == DetectionStatus.OFF]
        self.assertEqual(len(offed_reports), 0)

        unavail_reports = [r for r in reports
                           if r.detectionStatus == DetectionStatus.UNAVAILABLE]
        self.assertEqual(len(unavail_reports), 0)

        reports_dir = os.path.join(self.analyzer_reports_dir, 'v2',
                                   'disable_dividezero_checker')
        test_files_dir = os.path.join(self.source_files_dir, 'v2')
        self.store(reports_dir, test_files_dir)

        reports = self._cc_client.getRunResults(None,
                                                100,
                                                0,
                                                [],
                                                None,
                                                None)
        print(reports)
        offed_reports = [r for r in reports
                         if r.detectionStatus == DetectionStatus.OFF]
        self.assertEqual(len(offed_reports), 1)

        unavail_reports = [r for r in reports
                           if r.detectionStatus == DetectionStatus.UNAVAILABLE]
        self.assertEqual(len(unavail_reports), 0)
