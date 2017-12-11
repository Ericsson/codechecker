#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
    report_server_api function tests.
"""

from collections import defaultdict
import os
import random
import shutil
import string
import unittest
from uuid import uuid4

from libtest import env
from libtest import codechecker

from codeCheckerDBAccess_v6.ttypes import Encoding


def _generate_content(cols, lines):
    """Generates a random file content string."""

    content = ""
    for _ in range(1, lines):
        for _ in range(1, cols):
            content += random.choice(string.letters)
        content += '\n'
    return content


def _replace_path(file_path, path):
    with open(file_path, 'r') as f:
        content = f.read().replace('$$$', path)
    with open(file_path, 'w') as f:
        f.write(content)


class HashClash(unittest.TestCase):
    """Unit test for testing hash clash handling."""

    def setUp(self):
        """
        Not much setup is needed.
        Runs and results are automatically generated.
        """

        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._report = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._report)

        # Store runs to check.
        self._codechecker_cfg = env.import_codechecker_cfg(test_workspace)

        source_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        self._test_dir = os.path.join(test_workspace, 'test_files')

        shutil.copytree(source_dir, self._test_dir)

        _replace_path(os.path.join(self._test_dir, 'run.plist'),
                      self._test_dir)

        codechecker.store(self._codechecker_cfg,
                          'test_hash_clash_' + uuid4().hex,
                          self._test_dir)

    def _reports_for_latest_run(self):
        runs = self._report.getRunData(None)
        max_run_id = max(map(lambda run: run.runId, runs))
        return self._report.getRunResults([max_run_id],
                                          100,
                                          0,
                                          [],
                                          None,
                                          None)

    def test_hash_clash(self):
        """Runs the following tests:

        - Duplicates.
        - Hash clash in same file.
        - Hash clash in different files.
        - Hash clash in different build actions.
        """
        reports = self._reports_for_latest_run()

        # The PList file contains six bugs:
        # 1. A normal bug
        # 2. Same as the first one (no new report generated)
        # 3. Same as the first one except for line numbers (new report
        #    generated)
        # 4. Same as the first one except for column numbers (new report
        #    generated)
        # 5. Same as the first one except for the file name (new report
        #    generated)
        # 6. Same as the first one except for the checker message (new report
        #    generated)

        fileid1 = None
        fileid2 = None

        for report in reports:
            f = self._report.getSourceFileData(report.fileId,
                                               False,
                                               Encoding.BASE64)

            if f.filePath.endswith('main.cpp'):
                fileid1 = f.fileId
            elif f.filePath.endswith('main2.cpp'):
                fileid2 = f.fileId

        by_file = defaultdict(int)
        for report in reports:
            by_file[report.fileId] += 1

        self.assertEqual(by_file[fileid1], 4)
        self.assertEqual(by_file[fileid2], 1)

        by_checker_message = defaultdict(int)
        for report in reports:
            by_checker_message[report.checkerMsg] += 1

        self.assertEqual(by_checker_message['checker message'], 4)
        self.assertEqual(by_checker_message['checker message 2'], 1)
