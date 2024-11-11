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

from libtest import codechecker
from libtest import env
from libtest import plist_test


class CppCheck(unittest.TestCase):
    """
    Test storage of cppcheck reports
    """

    def setup_class(self):
        """Setup the environment for the tests then start the server."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('cppcheck')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        # Configuration options.
        codechecker_cfg = {
            'suppress_file': None,
            'skip_list_file': None,
            'check_env': env.test_env(TEST_WORKSPACE),
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
            'test_project': 'cppcheck'
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'cppcheck'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

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
        for report in reports:
            # The stored hash should not be "0".
            self.assertNotEqual(report["bugHash"], "0")
            # The stored checker name should not be the fake(d) default that
            # was created because no 'metadata.json' (and thus no checker
            # list) exists for this "project".
            self.assertNotEqual(report["checkerId"], "__FAKE__")
