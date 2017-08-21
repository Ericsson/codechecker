#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" detection_status function test. """
import json
import os
import unittest

import shared

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
        makefile = "all:\n\t$(CXX) -c main.cpp -o /dev/null\n"
        project_info = {
            "name": "hello",
            "clean_cmd": "",
            "build_cmd": "make"
        }

        with open(os.path.join(self._test_dir, 'Makefile'), 'w') as f:
            f.write(makefile)
        with open(os.path.join(self._test_dir, 'project_info.json'), 'w') as f:
            json.dump(project_info, f)

    def tearDown(self):
        """Restore environment after tests have ran."""
        os.chdir(self.__old_pwd)

    def _create_source_file(self, version):
        if version == 1:
            source = """
int main()
{
  int i = 1 / 0;
}"""
        elif version == 2:
            source = """
int main()
{
  int i = 1 / 0;

  int* p = 0;

  i = *p + 42;
}"""
        elif version == 3:
            source = """
int main()
{
  int i = 1 / 2;

  int* p = 0;

  i = *p + 42;
}"""
        elif version == 4:
            source = """


int main()
{
  int i = 1 / 0;

  int* p = 0;

  i = *p + 42;
}"""

        with open(os.path.join(self._test_dir, self._source_file), 'w') as f:
            f.write(source)

        codechecker.check(self._codechecker_cfg,
                          'hello',
                          self._test_dir)

    def test_same_file_change(self):
        """
        This tests the change of the detection status of bugs when the file
        content changes.
        """

        # Check the first file version
        self._create_source_file(1)

        runs = self._cc_client.getRunData(None)
        run_id = max(map(lambda run: run.runId, runs))

        reports = self._cc_client.getRunResults(run_id, 100, 0, {}, {})
        self.assertEqual(len(reports), 2)
        self.assertTrue(all(map(
            lambda r: r.detectionStatus == shared.ttypes.DetectionStatus.NEW,
            reports)))

        # Check the second file version
        self._create_source_file(2)
        reports = self._cc_client.getRunResults(run_id, 100, 0, {}, {})
        for report in reports:
            if report.detectionStatus == \
                    shared.ttypes.DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])
            elif report.detectionStatus == \
                    shared.ttypes.DetectionStatus.NEW:
                self.assertIn(report.bugHash,
                              ['cbd629ba2ee25c41cdbf5e2e336b1b1c'])
            else:
                self.assertTrue(False)

        # Check the third file version
        self._create_source_file(3)
        reports = self._cc_client.getRunResults(run_id, 100, 0, {}, {})
        for report in reports:
            if report.detectionStatus == \
                    shared.ttypes.DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])
            elif report.detectionStatus == \
                    shared.ttypes.DetectionStatus.NEW:
                self.assertIn(report.bugHash,
                              ['ac147b31a745d91be093bd70bbc5567c'])
            elif report.detectionStatus == \
                    shared.ttypes.DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['cbd629ba2ee25c41cdbf5e2e336b1b1c'])
            else:
                self.assertTrue(False)

        # Check the second file version again
        self._create_source_file(2)
        reports = self._cc_client.getRunResults(run_id, 100, 0, {}, {})
        for report in reports:
            if report.detectionStatus == \
                    shared.ttypes.DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['cbd629ba2ee25c41cdbf5e2e336b1b1c'])
            elif report.detectionStatus == \
                    shared.ttypes.DetectionStatus.REOPENED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])
            elif report.detectionStatus == \
                    shared.ttypes.DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['ac147b31a745d91be093bd70bbc5567c'])

        # Check the fourth file version
        self._create_source_file(4)
        reports = self._cc_client.getRunResults(run_id, 100, 0, {}, {})
        for report in reports:
            if report.detectionStatus == \
                    shared.ttypes.DetectionStatus.UNRESOLVED:
                self.assertIn(report.bugHash,
                              ['cbd629ba2ee25c41cdbf5e2e336b1b1c'])
            elif report.detectionStatus == \
                    shared.ttypes.DetectionStatus.REOPENED:
                self.assertIn(report.bugHash,
                              ['209be2f6905590d99853ce01d52a78e0',
                               'e8f47588c8095f02a53e338984ce52ba'])
            elif report.detectionStatus == \
                    shared.ttypes.DetectionStatus.RESOLVED:
                self.assertIn(report.bugHash,
                              ['ac147b31a745d91be093bd70bbc5567c'])
