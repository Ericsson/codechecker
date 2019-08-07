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

import json
import os
import unittest

from codeCheckerDBAccess_v6.ttypes import *

from libtest import codechecker
from libtest import env


class TestDetectionStatus(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._test_dir = os.path.join(self.test_workspace, 'test_files')

        try:
            os.makedirs(self._test_dir)
        except os.error:
            # Directory already exists.
            pass

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Change working dir to testfile dir so CodeChecker can be run easily.
        self.__old_pwd = os.getcwd()
        os.chdir(self._test_dir)

        self._source_file = "main.cpp"

        # Init project dir.
        makefile = "all:\n\t$(CXX) -c main.cpp -Wno-division-by-zero " \
                   "-Wno-all -Wno-extra -o /dev/null\n"
        project_info = {
            "name": "hello",
            "clean_cmd": "",
            "build_cmd": "make"
        }

        with open(os.path.join(self._test_dir, 'Makefile'), 'w') as f:
            f.write(makefile)
        with open(os.path.join(self._test_dir, 'project_info.json'), 'w') as f:
            json.dump(project_info, f)

        self.sources = ["""
int main()
{
  int i = 1 / 0;

  sizeof(42);
  sizeof(42);
  sizeof(42);
}""", """
int main()
{
  int i = 1 / 0;

  int* p = 0;

  i = *p + 42;

  sizeof(42);
  sizeof(42);
  sizeof(42);
}""", """
int main()
{
  int i = 1 / 2;

  int* p = 0;

  i = *p + 42;

  sizeof(42);
  sizeof(42);
  sizeof(42);
}""", """


int main()
{
  int i = 1 / 0;

  int* p = 0;

  i = *p + 42;

  sizeof(42);
  sizeof(42);
}"""]

    def tearDown(self):
        """Restore environment after tests have ran."""
        os.chdir(self.__old_pwd)

    def _create_source_file(self, version):
        with open(os.path.join(self._test_dir, self._source_file), 'w') as f:
            f.write(self.sources[version])

    def _check_source_file(self, cfg):
        codechecker.check_and_store(cfg, 'hello', self._test_dir)

    def test_same_file_change(self):
        """
        This tests the change of the detection status of bugs when the file
        content changes.
        """
        runs = self._cc_client.getRunData(None, None, 0, None)

        if runs:
            run_id = max(map(lambda run: run.runId, runs))
            self._cc_client.removeRun(run_id)

        # Check the first file version
        self._create_source_file(0)
        self._check_source_file(self._codechecker_cfg)

        runs = self._cc_client.getRunData(None, None, 0, None)
        run_id = max(map(lambda run: run.runId, runs))

        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)

        self.assertEqual(len(reports), 5)
        self.assertTrue(all(map(
            lambda r: r.detectionStatus == DetectionStatus.NEW,
            reports)))

        # Check the second file version
        self._create_source_file(1)
        self._check_source_file(self._codechecker_cfg)
        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)
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

        # Check the third file version
        self._create_source_file(2)
        self._check_source_file(self._codechecker_cfg)
        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)
        for report in reports:
            if report.detectionStatus == DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])

                file_content = self._cc_client.getSourceFileData(
                    report.fileId,
                    True,
                    Encoding.DEFAULT).fileContent

                self.assertEqual(
                    file_content,
                    self.sources[1],
                    "Resolved bugs should be shown with the old file content.")

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

                self.assertEqual(
                    file_content,
                    self.sources[2],
                    "Unresolved bug should be shown with the new file "
                    "content.")

            else:
                self.assertTrue(False)

        # Check the second file version again
        self._create_source_file(1)
        self._check_source_file(self._codechecker_cfg)
        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)
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
        self._create_source_file(3)
        self._check_source_file(self._codechecker_cfg)
        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)
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

                self.assertEqual(
                    file_content,
                    self.sources[3],
                    "Reopened bugs should be shown with the new file content.")

            elif report.detectionStatus == DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['ac147b31a745d91be093bd70bbc5567c'])

    def test_check_without_metadata(self):
        """
        This test checks whether the storage works without a metadata.json.
        """
        runs = self._cc_client.getRunData(None, None, 0, None)
        if runs:
            run_id = max(map(lambda run: run.runId, runs))

            # Remove the run.
            self._cc_client.removeRun(run_id)

        self._create_source_file(0)

        codechecker.log_and_analyze(self._codechecker_cfg,
                                    self._test_dir)

        try:
            # Test storage without metadata.json.
            os.remove(os.path.join(self._codechecker_cfg['reportdir'],
                                   'metadata.json'))
        except OSError:
            # metadata.json already removed.
            pass

        codechecker.store(self._codechecker_cfg, 'hello')

        runs = self._cc_client.getRunData(None, None, 0, None)
        run_id = max(map(lambda run: run.runId, runs))

        reports = self._cc_client.getRunResults([run_id],
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)

        self.assertEqual(len(reports), 2)

    def test_detection_status_off(self):
        """
        This test checks reports which have detection status of 'Off'.
        """
        runs = self._cc_client.getRunData(None, None, 0, None)
        if runs:
            run_id = max(map(lambda run: run.runId, runs))

            # Remove the run.
            self._cc_client.removeRun(run_id)

        cfg = dict(self._codechecker_cfg)

        self._create_source_file(0)
        self._check_source_file(cfg)

        self._create_source_file(1)
        self._check_source_file(cfg)

        reports = self._cc_client.getRunResults(None,
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)
        offed_reports = [r for r in reports
                         if r.detectionStatus == DetectionStatus.OFF]
        self.assertEqual(len(offed_reports), 0)

        unavail_reports = [r for r in reports
                           if r.detectionStatus == DetectionStatus.UNAVAILABLE]
        self.assertEqual(len(unavail_reports), 0)

        cfg['checkers'] = ['-d', 'core.DivideZero']

        self._create_source_file(1)
        self._check_source_file(cfg)

        reports = self._cc_client.getRunResults(None,
                                                100,
                                                0,
                                                [],
                                                None,
                                                None,
                                                False)
        print(reports)
        offed_reports = [r for r in reports
                         if r.detectionStatus == DetectionStatus.OFF]
        self.assertEqual(len(offed_reports), 1)

        unavail_reports = [r for r in reports
                           if r.detectionStatus == DetectionStatus.UNAVAILABLE]
        self.assertEqual(len(unavail_reports), 0)
