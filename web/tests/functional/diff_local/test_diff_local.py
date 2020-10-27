#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""diff_local function test.

Diff local tests the diff comarison feature between local report directories.

"""


import json
import os
import re
import subprocess
import unittest

from libtest import env


class DiffLocal(unittest.TestCase):

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

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        self.base_reports = self._test_cfg['codechecker_cfg']['reportdir_base']
        self.new_reports = self._test_cfg['codechecker_cfg']['reportdir_new']

    def test_resolved_json(self):
        """Get the resolved reports.

        core.CallAndMessage checker was disabled in the new run, those
        reports should be listed as resolved.
        """
        unresolved_diff_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                               '-b', self.base_reports,
                               '-n', self.new_reports,
                               '--resolved', '-o', 'json']
        print(unresolved_diff_cmd)
        out_json = subprocess.check_output(
            unresolved_diff_cmd, encoding="utf-8", errors="ignore")
        resolved_results = json.loads(out_json)
        print(resolved_results)

        for resolved in resolved_results:
            self.assertEqual(resolved['checkerId'], "core.CallAndMessage")

    def test_new_json(self):
        """Get the new reports.

        core.StackAddressEscape checker was enabled in the new run, those
        reports should be listed as new.
        """
        new_diff_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                        '-b', self.base_reports,
                        '-n', self.new_reports,
                        '--new', '-o', 'json']
        print(new_diff_cmd)
        out_json = subprocess.check_output(
            new_diff_cmd, encoding="utf-8", errors="ignore")
        resolved_results = json.loads(out_json)
        print(resolved_results)

        for resolved in resolved_results:
            self.assertEqual(resolved['checkerId'], "core.NullDereference")

    @unittest.skip("should return a valid empty json")
    def test_filter_severity_low_json(self):
        """Get the low severity new reports.

        core.StackAddressEscape checker was enabled in the new run, those
        reports should be listed as new.
        """
        low_severity_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                            '-b', self.base_reports,
                            '-n', self.new_reports,
                            '--severity', 'low',
                            '--new', '-o', 'json']
        print(low_severity_cmd)
        out_json = subprocess.check_output(
            low_severity_cmd, encoding="utf-8", errors="ignore")
        print(out_json)
        low_severity_res = json.loads(out_json)
        self.assertEqual((len(low_severity_res)), 0)
        print(low_severity_res)

    def test_filter_severity_high_json(self):
        """Get the high severity new reports.

        core.StackAddressEscape checker (high severity) was enabled
        in the new run, those reports should be listed.
        """
        high_severity_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                             '-b', self.base_reports,
                             '-n', self.new_reports,
                             '--severity', 'high',
                             '--new', '-o', 'json']
        print(high_severity_cmd)
        try:
            out_json = subprocess.check_output(
                high_severity_cmd, encoding="utf-8", errors="ignore")
        except subprocess.CalledProcessError as cerr:
            print(cerr.output)
        high_severity_res = json.loads(out_json)
        self.assertEqual((len(high_severity_res)), 4)

    def test_filter_severity_high_text(self):
        """Get the high severity new reports.

        core.StackAddressEscape checker (high severity) was enabled
        in the new run, those reports should be listed.
        """
        high_severity_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                             '-b', self.base_reports,
                             '-n', self.new_reports,
                             '--severity', 'high',
                             '--new']
        print(high_severity_cmd)
        out = subprocess.check_output(
            high_severity_cmd,
            encoding="utf-8",
            errors="ignore")
        print(out)
        self.assertEqual(len(re.findall(r'\[HIGH\]', out)), 4)
        self.assertEqual(len(re.findall(r'\[LOW\]', out)), 0)

    def test_filter_severity_high_low_text(self):
        """Get the high and low severity unresolved reports."""
        high_severity_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                             '-b', self.base_reports,
                             '-n', self.new_reports,
                             '--severity', 'high', 'low',
                             '--unresolved']
        print(high_severity_cmd)
        try:
            out = subprocess.check_output(
                high_severity_cmd,
                encoding="utf-8",
                errors="ignore")
        except subprocess.CalledProcessError as cerr:
            print(cerr.stdout)
            print(cerr.stderr)
        self.assertEqual(len(re.findall(r'\[HIGH\]', out)), 15)
        self.assertEqual(len(re.findall(r'\[LOW\]', out)), 6)

    @unittest.skip("fix test if severity will be"
                   "available in the json output.")
    def test_filter_severity_high_low_json(self):
        """Get the high and low severity unresolved reports in json."""
        high_severity_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                             '-b', self.base_reports,
                             '-n', self.new_reports,
                             '--severity', 'high', 'low',
                             '--unresolved', '-o', 'json']
        print(high_severity_cmd)
        out_json = subprocess.check_output(
            high_severity_cmd, encoding="utf-8", errors="ignore")
        print(out_json)
        high_low_unresolved_results = json.loads(out_json)
        print(high_low_unresolved_results)

        # FIXME check json output for the returned severity levels.

    def test_multiple_dir(self):
        """ Get unresolved reports from muliple local directories. """
        unresolved_diff_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                               '-b', self.base_reports, self.new_reports,
                               '-n', self.new_reports, self.base_reports,
                               '--unresolved', '-o', 'json']
        print(unresolved_diff_cmd)
        out_json = subprocess.check_output(
            unresolved_diff_cmd, encoding="utf-8", errors="ignore")
        print(out_json)
        unresolved_results = json.loads(out_json)
        self.assertNotEqual(len(unresolved_results), 0)

    def test_missing_source_file(self):
        """ Get reports when a source file is missing. """
        new_diff_cmd = [self._codechecker_cmd, 'cmd', 'diff',
                        '-b', self.base_reports,
                        '-n', self.new_reports,
                        '--new']

        # Rename an existing source file related to a report to make sure
        # there is at least one missing source file.
        old_file_path = os.path.join(
            self._testproject_data["project_path_new"],
            "null_dereference.cpp")
        new_file_path = old_file_path + "_renamed"
        os.rename(old_file_path, new_file_path)

        proc = subprocess.Popen(
            new_diff_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")

        _, err = proc.communicate()
        self.assertIn("source file contents changed", err)

        # Rename the file back.
        os.rename(new_file_path, old_file_path)
