#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
cppcheck tests.
"""


import json
import os
import shutil
import subprocess
import unittest

from libtest import env
from libtest import plist_test


class CppCheck(unittest.TestCase):
    """
    Test storage of cppcheck reports
    """

    def setUp(self):

        # Get the test workspace used to cppcheck tests.
        self._test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._test_cfg = env.import_test_cfg(self._test_workspace)

    def test_cppcheck_report_storage(self):
        """ In the stored report not the default zero hash should be used. """

        test_dir = os.path.dirname(os.path.realpath(__file__))

        report_dir = os.path.join(test_dir, 'test_proj')

        codechecker_cfg = self._test_cfg['codechecker_cfg']

        # Copy report files to a temporary directory not to modify the
        # files in the repository.
        # Report files will be overwritten during the tests.
        temp_workspace = os.path.join(codechecker_cfg['workspace'],
                                      'test_proj')
        shutil.copytree(report_dir, temp_workspace)

        report_file = os.path.join(temp_workspace, 'divide_zero.plist')
        # Convert file paths to absolute in the report.
        plist_test.prefix_file_path(report_file, temp_workspace)

        run_name = 'cppcheck'
        store_cmd = [env.codechecker_cmd(), 'store', '--name', run_name,
                     # Use the 'Default' product.
                     '--url', env.parts_to_url(codechecker_cfg),
                     temp_workspace]

        out = subprocess.check_output(
            store_cmd, encoding="utf-8", errors="ignore")
        print(out)
        query_cmd = [env.codechecker_cmd(), 'cmd', 'results', run_name,
                     # Use the 'Default' product.
                     '--url', env.parts_to_url(codechecker_cfg), '-o', 'json']

        out = subprocess.check_output(
            query_cmd, encoding="utf-8", errors="ignore")
        print(out)
        reports = json.loads(out)
        self.assertEqual(len(reports), 5)
        # The stored hash should not be "0".
        for report in reports:
            self.assertNotEqual(report['bugHash'], "0")
