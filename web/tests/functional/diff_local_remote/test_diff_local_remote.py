#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""diff_local_remote function test.

Tests for the diff feature when comparing a local report directory
with a remote run in the database.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import os
import re
import subprocess
import unittest

from libtest import env


class LocalRemote(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        self._test_cfg = env.import_test_cfg(test_workspace)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        # Get the run names which belong to this test.
        self._run_names = env.get_run_names(test_workspace)

        local_test_project = \
            self._test_cfg['test_project']['project_path_local']

        self._local_reports = os.path.join(local_test_project, 'reports')

        self._url = env.parts_to_url(self._test_cfg['codechecker_cfg'])

        self._env = self._test_cfg['codechecker_cfg']['check_env']

    def run_cmd(self, diff_cmd):
        print(diff_cmd)
        out = subprocess.check_output(diff_cmd,
                                      env=self._env,
                                      cwd=os.environ['TEST_WORKSPACE'])
        print(out)
        return out

    def get_local_remote_diff(self, extra_args=None):
        """Return the unresolved results comparing local to a remote.

        Returns the text output of the diff command comparing the
        local reports to a remote run in the database.

        extra_args: can be used to add list of additional
                    arguments to the diff command.
                    Like filter arguments or to change output format.
        """
        remote_run_name = self._run_names[0]

        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--unresolved",
                    "--url", self._url,
                    "-b", self._local_reports,
                    "-n", remote_run_name
                    ]
        if extra_args:
            diff_cmd.extend(extra_args)

        print(diff_cmd)
        out = subprocess.check_output(diff_cmd,
                                      env=self._env,
                                      cwd=os.environ['TEST_WORKSPACE'])
        print(out)
        return out

    def test_local_to_remote_compare_count_new(self):
        """Count the new results with no filter in local compare mode."""
        base_run_name = self._run_names[0]
        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--new",
                    "--url", self._url,
                    "-b", self._local_reports,
                    "-n", base_run_name
                    ]

        out = self.run_cmd(diff_cmd)

        count = len(re.findall(r'\[core\.NullDereference\]', out))

        self.assertEqual(count, 4)

    def test_remote_to_local_compare_count_new(self):
        """Count the new results with no filter."""
        base_run_name = self._run_names[0]
        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--new",
                    "--url", self._url,
                    "-b", base_run_name,
                    "-n", self._local_reports
                    ]

        out = self.run_cmd(diff_cmd)

        # 5 new core.CallAndMessage issues.
        # 1 is suppressed in code
        count = len(re.findall(r'\[core\.CallAndMessage\]', out))
        self.assertEqual(count, 4)

        # core.NullDereference was disabled in the remote analysis
        # so no results are new comapared to the local analysis.
        count = len(re.findall(r'\[core\.NullDereference\]', out))
        self.assertEqual(count, 0)

    def test_local_compare_count_unres(self):
        """Count the unresolved results with no filter."""
        base_run_name = self._run_names[0]
        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--unresolved",
                    "--url", self._url,
                    "-b", self._local_reports,
                    "-n", base_run_name
                    ]

        out = self.run_cmd(diff_cmd)

        print(out)

        count = len(re.findall(r'\[core\.CallAndMessage\]', out))
        self.assertEqual(count, 0)
        count = len(re.findall(r'\[core\.DivideZero\]', out))
        self.assertEqual(count, 10)
        count = len(re.findall(r'\[deadcode\.DeadStores\]', out))
        self.assertEqual(count, 6)
        count = len(re.findall(r'\[cplusplus\.NewDelete\]', out))
        self.assertEqual(count, 5)
        count = len(re.findall(r'\[unix\.Malloc\]', out))
        self.assertEqual(count, 1)

    def test_local_compare_count_unres_rgx(self):
        """Count the unresolved results with no filter and run name regex."""
        base_run_name = self._run_names[0]

        # Change test_files_blablabla to test_*_blablabla
        base_run_name = base_run_name.replace('files', '*')

        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--unresolved",
                    "--url", self._url,
                    "-b", self._local_reports,
                    "-n", base_run_name
                    ]

        out = self.run_cmd(diff_cmd)

        print(out)

        count = len(re.findall(r'\[core\.CallAndMessage\]', out))
        self.assertEqual(count, 0)
        count = len(re.findall(r'\[core\.DivideZero\]', out))
        self.assertEqual(count, 10)
        count = len(re.findall(r'\[deadcode\.DeadStores\]', out))
        self.assertEqual(count, 6)
        count = len(re.findall(r'\[cplusplus\.NewDelete\]', out))
        self.assertEqual(count, 5)
        count = len(re.findall(r'\[unix\.Malloc\]', out))
        self.assertEqual(count, 1)

    def test_local_cmp_filter_unres_severity(self):
        """Filter unresolved results by severity levels."""
        res = self.get_local_remote_diff(['--severity', 'low'])
        self.assertEqual(len(re.findall(r'\[LOW\]', res)), 6)
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 0)

        res = self.get_local_remote_diff(['--severity', 'high'])
        self.assertEqual(len(re.findall(r'\[LOW\]', res)), 0)
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 18)

        res = self.get_local_remote_diff(['--severity', 'high', 'low'])
        self.assertEqual(len(re.findall(r'\[LOW\]', res)), 6)
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 18)

        res = self.get_local_remote_diff()
        self.assertEqual(len(re.findall(r'\[LOW\]', res)), 6)
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 18)

    def test_local_cmp_filter_unres_filepath(self):
        """Filter unresolved results by file path."""
        res = self.get_local_remote_diff(['--file', '*divide_zero.cpp'])
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 4)
        self.assertEqual(len(re.findall(r'new_delete.cpp', res)), 0)

        res = self.get_local_remote_diff(['--file',
                                          'divide_zero.cpp',  # Exact match.
                                          '*new_delete.cpp'])
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 0)
        self.assertEqual(len(re.findall(r'new_delete.cpp', res)), 6)

    def test_local_cmp_filter_unres_checker_name(self):
        """Filter by checker name."""
        res = self.get_local_remote_diff(['--checker-name',
                                          'core.NullDereference'])
        self.assertEqual(len(re.findall(r'core.NullDereference', res)), 0)

        res = self.get_local_remote_diff(['--checker-name', 'core.*'])
        self.assertEqual(len(re.findall(r'core.*', res)), 13)

        # Filter by checker message (case insensitive).
        res = self.get_local_remote_diff(['--checker-msg', 'division by*'])
        self.assertEqual(len(re.findall(r'Division by.*', res)), 10)

    def test_local_cmp_filter_unres_filter_mix(self):
        """Filter by multiple filters file and severity."""
        res = self.get_local_remote_diff(['--file', '*divide_zero.cpp',
                                          '--severity', 'high'])
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 2)
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 2)

    def test_local_cmp_filter_unres_filter_mix_json(self):
        """Filter by multiple filters file and severity with json output."""
        # TODO check if only high severity reports are retuned.
        res = self.get_local_remote_diff(['--file', '*divide_zero.cpp',
                                          '--severity', 'high',
                                          '-o', 'json'])
        reports = json.loads(res)
        for report in reports:
            print(report)
            self.assertTrue("divide_zero.cpp" in report['checkedFile'],
                            "Report filename is different from the expected.")

    def test_local_compare_res_html_output_unresolved(self):
        """Check that html files will be generated by using diff command."""
        base_run_name = self._run_names[0]

        html_reports = os.path.join(self._local_reports, "html_reports")

        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--unresolved",
                    "--url", self._url,
                    "-b", base_run_name,
                    "-n", self._local_reports,
                    "-o", "html",
                    "-e", html_reports
                    ]

        print(diff_cmd)
        out = subprocess.check_output(diff_cmd, env=self._env,
                                      cwd=os.environ['TEST_WORKSPACE'])
        print(out)

        diff_res = json.loads(self.get_local_remote_diff(['-o', 'json']))

        checked_files = set()
        for res in diff_res:
            print(res)
            checked_files.add(os.path.basename(res['checkedFile']))

        # Check if index.html file was generated.
        html_index = os.path.join(html_reports, "index.html")
        self.assertTrue(os.path.exists(html_index))

        # Check that html files were generated for each reports.
        for html_file_names in os.listdir(html_reports):
            suffix = html_file_names.rfind("_")
            file_name = html_file_names[:suffix] \
                if suffix != -1 else html_file_names

            if file_name == "index.html":
                continue

            self.assertIn(file_name, checked_files)
