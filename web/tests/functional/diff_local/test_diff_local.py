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

from libtest import env, codechecker
from libtest.codechecker import get_diff_results


class DiffLocal(unittest.TestCase):

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        self._test_cfg = env.import_test_cfg(test_workspace)
        self._codechecker_cfg = self._test_cfg['codechecker_cfg']
        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._test_dir = os.path.join(test_workspace, 'test_files')
        try:
            os.makedirs(self._test_dir)
        except os.error:
            # Directory already exists.
            pass

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        self.base_reports = self._codechecker_cfg['reportdir_base']
        self.new_reports = self._codechecker_cfg['reportdir_new']

    def test_resolved_json(self):
        """Get the resolved reports.

        core.CallAndMessage checker was disabled in the new run, those
        reports should be listed as resolved.
        """
        resolved_results, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--resolved', 'json')
        print(resolved_results)

        for resolved in resolved_results:
            self.assertEqual(resolved['checkerId'], "core.CallAndMessage")

    def test_new_json(self):
        """Get the new reports.

        core.StackAddressEscape checker was enabled in the new run, those
        reports should be listed as new.
        """
        new_results, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--new', 'json')
        print(new_results)

        for new_result in new_results:
            self.assertEqual(new_result['checkerId'], "core.NullDereference")

    def test_non_existent_reports_directory(self):
        """Handles non existent directory well

        Displays detailed information about base and new directories when
        any of them are not exist.
        """
        _, error_output, return_code = get_diff_results(
            [self.base_reports], ['unexistent-dir-name'], '--new',
            extra_args=['--url', f"localhost:{env.get_free_port()}/Default"])

        self.assertEqual(return_code, 1,
                         "Exit code should be 1 if directory does not exist.")
        self.assertIn("Failed to get remote runs from server", error_output)

    @unittest.skip("should return a valid empty json")
    def test_filter_severity_low_json(self):
        """Get the low severity new reports.

        core.StackAddressEscape checker was enabled in the new run, those
        reports should be listed as new.
        """
        low_severity_res, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--new', 'json',
            ['--severity', 'low'])
        print(low_severity_res)

        self.assertEqual((len(low_severity_res)), 0)

    def test_filter_severity_high_json(self):
        """Get the high severity new reports.

        core.StackAddressEscape checker (high severity) was enabled
        in the new run, those reports should be listed.
        """
        high_severity_res, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--new', 'json',
            ['--severity', 'high'])
        self.assertEqual(len(high_severity_res), 4)

    def test_filter_severity_high_text(self):
        """Get the high severity new reports.

        core.StackAddressEscape checker (high severity) was enabled
        in the new run, those reports should be listed.
        """
        out, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--new', None,
            ['--severity', 'high'])
        print(out)
        self.assertEqual(len(re.findall(r'\[HIGH\]', out)), 4)
        self.assertEqual(len(re.findall(r'\[LOW\]', out)), 0)

    def test_filter_severity_high_low_text(self):
        """Get the high and low severity unresolved reports."""
        out, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--unresolved', None,
            ['--severity', 'high', 'low'])
        self.assertEqual(len(re.findall(r'\[HIGH\]', out)), 18)
        self.assertEqual(len(re.findall(r'\[LOW\]', out)), 6)

    @unittest.skip("fix test if severity will be"
                   "available in the json output.")
    def test_filter_severity_high_low_json(self):
        """Get the high and low severity unresolved reports in json."""
        high_low_unresolved_results, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--unresolved', 'json',
            ['--severity', 'high', 'low'])
        print(high_low_unresolved_results)

        # FIXME check json output for the returned severity levels.

    def test_multiple_dir(self):
        """ Get unresolved reports from muliple local directories. """
        unresolved_results, _, _ = get_diff_results(
            [self.base_reports, self.new_reports],
            [self.new_reports, self.base_reports],
            '--unresolved', 'json',
            ['--severity', 'high', 'low'])
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

    def test_suppress_reports(self):
        """
        Check diff command when analysing the same source file which contains
        source code comments.
        """
        cfg = dict(self._codechecker_cfg)
        cfg['analyzers'] = ['clang-tidy']

        makefile = f"all:\n\t$(CXX) -c main.cpp -Wno-all -Wno-extra " \
                   f"-o /dev/null\n"
        with open(os.path.join(self._test_dir, 'Makefile'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(makefile)

        project_info = {
            "name": "suppress",
            "clean_cmd": "",
            "build_cmd": "make"
        }
        with open(os.path.join(self._test_dir, 'project_info.json'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            json.dump(project_info, f)

        # 1st phase.
        content = """
int main()
{
  sizeof(41);

  sizeof(42);

  sizeof(43);
}"""

        with open(os.path.join(self._test_dir, "main.cpp"), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(content)

        report_dir_base = os.path.join(self._test_dir, "reports1")
        cfg['reportdir'] = report_dir_base

        codechecker.log_and_analyze(cfg, self._test_dir)

        # 2nd phase.
        content = """
int main()
{
  // codechecker_intentional [all] This bug is suppressed in this change.
  sizeof(41);

  sizeof(42);

  // codechecker_confirmed [all] This bug is a real bug
  sizeof(44);

  sizeof(45);
}"""
        with open(os.path.join(self._test_dir, "main.cpp"), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(content)

        report_dir_new = os.path.join(self._test_dir, "reports2")
        cfg['reportdir'] = report_dir_new

        codechecker.log_and_analyze(cfg, self._test_dir)

        # Run the diff command and check the results.
        res, _, _ = get_diff_results(
            [report_dir_base], [report_dir_new], '--new', 'json')
        print(res)
        self.assertEqual(len(res), 2)

        res, _, _ = get_diff_results(
            [report_dir_base], [report_dir_new], '--unresolved', 'json')
        self.assertEqual(len(res), 1)

        res, _, _ = get_diff_results(
            [report_dir_base], [report_dir_new], '--resolved', 'json')
        self.assertEqual(len(res), 2)
