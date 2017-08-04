# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test source-code level suppression data writing to suppress file.
"""

import logging
import os
import shlex
import subprocess
from subprocess import CalledProcessError
import unittest

from libtest import env
from libtest import codechecker
from libtest.thrift_client_to_db import get_all_run_results

import shared


class TestSuppress(unittest.TestCase):
    """
    Test source-code level suppression data writing to suppress file.
    """

    def setUp(self):
        self._test_workspace = os.environ['TEST_WORKSPACE']

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._test_project_path = self._testproject_data['project_path']

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test
        run_names = env.get_run_names(self._test_workspace)

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test.')
        self._runid = test_runs[0].runId
        self._run_name = test_runs[0].name

    def test_source_suppress_export(self):
        """
        Test exporting a source suppress comment automatically to file.
        """

        def __call(command):
            try:
                print(' '.join(command))
                proc = subprocess.Popen(shlex.split(' '.join(command)),
                                        cwd=self._test_project_path,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        env=env.test_env())
                out, err = proc.communicate()
                print(out)
                print(err)
                return 0
            except CalledProcessError as cerr:
                print("Failed to call:\n" + ' '.join(cerr.cmd))
                return cerr.returncode

        generated_file = os.path.join(self._test_workspace,
                                      "generated.suppress")

        extract_cmd = ['CodeChecker', 'parse',
                       os.path.join(self._test_workspace, "reports"),
                       "--suppress", generated_file,
                       "--export-source-suppress"
                       ]

        ret = __call(extract_cmd)
        self.assertEqual(ret, 0, "Failed to generate suppress file.")

        with open(generated_file, 'r') as generated:
            with open(os.path.join(self._test_project_path,
                      "suppress.expected"), 'r') as expected:
                self.assertEqual(generated.read().strip(),
                                 expected.read().strip(),
                                 "The generated suppress file does not "
                                 "look like what was expected.")

    def test_suppress_comment_in_db(self):
        """
        Exported source suppress comment stored as a review status in the db.
        """
        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug = run_results[0]

        report = self._cc_client.getReport(bug.reportId)

        # Check the stored suppress comment
        status = shared.ttypes.ReviewStatus.FALSE_POSITIVE
        self.assertEqual(report.review.comment, 'deliberate segfault!')
        self.assertEqual(report.review.status, status)

        # Change review status to confirmed bug.
        review_comment = 'This is really a bug'
        status = shared.ttypes.ReviewStatus.CONFIRMED
        success = self._cc_client.changeReviewStatus(
            bug.reportId, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        # Check the same project again.
        codechecker_cfg = env.import_test_cfg(
            self._test_workspace)['codechecker_cfg']

        initial_test_project_name = self._run_name

        ret = codechecker.check(codechecker_cfg,
                                initial_test_project_name,
                                self._test_project_path)
        if ret:
            sys.exit(1)

        # Get the results to compare.
        updated_results = get_all_run_results(self._cc_client, self._runid)
        self.assertIsNotNone(updated_results)
        self.assertNotEqual(len(updated_results), 0)

        bug = updated_results[0]

        report = self._cc_client.getReport(bug.reportId)

        # The stored suppress comment for the same bughash is the same.
        status = shared.ttypes.ReviewStatus.FALSE_POSITIVE
        self.assertEqual(report.review.comment, 'deliberate segfault!')
        self.assertEqual(report.review.status, status)
