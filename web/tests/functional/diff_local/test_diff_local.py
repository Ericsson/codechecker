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
import shutil
import subprocess
import sys
import unittest

from libtest import codechecker
from libtest import env
from libtest import project
from libtest.codechecker import create_baseline_file, get_diff_results


class DiffLocal(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing diff_local."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('diff_local')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        test_project = 'cpp'

        project_info = project.get_info(test_project)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path_base = os.path.join(TEST_WORKSPACE, "test_proj_base")
        shutil.copytree(project.path(test_project), test_proj_path_base)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path_new = os.path.join(TEST_WORKSPACE, "test_proj_new")
        shutil.copytree(project.path(test_project), test_proj_path_new)

        project_info['project_path_base'] = test_proj_path_base
        project_info['project_path_new'] = test_proj_path_new

        test_config['test_project'] = project_info

        # Suppress file should be set here if needed by the tests.
        suppress_file = None

        # Skip list file should be set here if needed by the tests.
        skip_list_file = None

        # Get an environment which should be used by the tests.
        test_env = env.test_env(TEST_WORKSPACE)

        # Create a basic CodeChecker config for the tests, this should
        # be imported by the tests and they should only depend on these
        # configuration options.
        codechecker_cfg = {
            'suppress_file': suppress_file,
            'skip_list_file': skip_list_file,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        # Base analysis
        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_base,
                                                    'reports')
        codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                       '-d', 'core.NullDereference']

        ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_base)
        if ret:
            sys.exit(1)

        # New analysis
        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_new,
                                                    'reports')
        codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                       '-e', 'core.NullDereference']

        ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_new)
        if ret:
            sys.exit(1)

        codechecker_cfg['reportdir_base'] = os.path.join(test_proj_path_base,
                                                         'reports')
        codechecker_cfg['reportdir_new'] = os.path.join(test_proj_path_new,
                                                        'reports')
        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE, test_config)

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, method):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the test configuration from the prepared into the test workspace.
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

        for resolved in resolved_results:
            self.assertEqual(resolved['checker_name'], "core.CallAndMessage")

    def test_missing_new_run(self):
        """
        Don't crash, but gracefully exit if -n is not specified.
        """
        _, err, return_code = get_diff_results(
            [self.base_reports], [], '--resolved', 'json')
        self.assertEqual(return_code, 1)
        self.assertIn("the following arguments are required: -n/--newname",
                      err)

    def test_missing_base_run(self):
        """
        Don't crash, but gracefully exit if -b is not specified.
        """
        _, err, return_code = get_diff_results(
            [], [self.new_reports], '--resolved', 'json')
        self.assertEqual(return_code, 1)
        self.assertIn("the following arguments are required: -b/--basename",
                      err)

    def test_new_json(self):
        """Get the new reports.

        core.StackAddressEscape checker was enabled in the new run, those
        reports should be listed as new.
        """
        new_results, _, _ = get_diff_results(
            [self.base_reports], [self.new_reports], '--new', 'json')
        print(new_results)

        for new_result in new_results:
            self.assertEqual(
                new_result['checker_name'], "core.NullDereference")

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

        # Change files' ctime to the current time in the report directory,
        # so the CodeChecker diff command will not see report files which
        # reference the previously renamed file older then the source file.
        for root, _, files in os.walk(self.new_reports):
            for file_name in files:
                os.utime(os.path.join(root, file_name))

    def test_suppress_reports(self):
        """
        Check diff command when analysing the same source file which contains
        source code comments.
        """
        cfg = dict(self._codechecker_cfg)

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
        self.assertEqual(len(res), 2)

        res, _, _ = get_diff_results(
            [report_dir_base], [report_dir_new], '--unresolved', 'json')
        self.assertEqual(len(res), 1)

        res, _, _ = get_diff_results(
            [report_dir_base], [report_dir_new], '--resolved', 'json')
        self.assertEqual(len(res), 2)

    def test_basename_baseline_file_json(self):
        """
        Get reports based on a baseline file given to the basename option.
        """
        baseline_file_path = create_baseline_file(self.base_reports)

        # Get new results.
        new_results, _, _ = get_diff_results(
            [baseline_file_path], [self.new_reports], '--new', 'json')

        print(new_results)

        for new_result in new_results:
            self.assertEqual(
                new_result['checker_name'], "core.NullDereference")

        # Get unresolved results.
        unresolved_results, _, _ = get_diff_results(
            [baseline_file_path], [self.new_reports], '--unresolved', 'json')

        print(unresolved_results)

        self.assertTrue(any(
            r for r in unresolved_results
            if r['checker_name'] == 'core.DivideZero'))

        self.assertFalse(any(
            r for r in unresolved_results
            if r['checker_name'] == 'core.NullDereference' or
            r['checker_name'] == 'core.CallAndMessage'))

        # Get resolved results.
        resolved_results, err, returncode = get_diff_results(
            [baseline_file_path], [self.new_reports], '--resolved', 'json')

        self.assertFalse(resolved_results)
        self.assertEqual(returncode, 2)
        self.assertIn(
            "Couldn't get local reports for the following baseline report "
            "hashes: ",
            err)

    def test_newname_baseline_file_json(self):
        """
        Get reports based on a baseline file given to the newname option.
        """
        baseline_file_path = create_baseline_file(self.new_reports)

        # Get new results.
        new_results, err, returncode = get_diff_results(
            [self.base_reports], [baseline_file_path], '--new', 'json')

        self.assertFalse(new_results)
        self.assertEqual(returncode, 2)
        self.assertIn(
            "Couldn't get local reports for the following baseline report "
            "hashes: ",
            err)

        # Get unresolved results.
        unresolved_results, err, returncode = get_diff_results(
            [self.base_reports], [baseline_file_path], '--unresolved', 'json')

        self.assertFalse(unresolved_results)
        self.assertEqual(returncode, 2)
        self.assertIn(
            "Couldn't get local reports for the following baseline report "
            "hashes: ",
            err)

        # Get resolved results.
        resolved_results, _, _ = get_diff_results(
            [self.base_reports], [baseline_file_path], '--resolved', 'json')

        for report in resolved_results:
            self.assertEqual(report['checker_name'], "core.CallAndMessage")

    def test_multiple_baseline_file_json(self):
        """ Test multiple baseline file for basename option. """
        baseline_file_paths = [
            create_baseline_file(self.base_reports),
            create_baseline_file(self.new_reports)]

        # Get new results.
        new_results, _, returncode = get_diff_results(
            baseline_file_paths, [self.new_reports], '--new', 'json')

        print(new_results)

        self.assertFalse(new_results)
        self.assertFalse(returncode)

        # Get unresolved results.
        unresolved_results, _, returncode = get_diff_results(
            baseline_file_paths, [self.new_reports], '--unresolved', 'json')
        print(unresolved_results)

        self.assertTrue(any(
            r for r in unresolved_results
            if r['checker_name'] == 'core.DivideZero'))

        # Get resolved results.
        resolved_results, err, returncode = get_diff_results(
            baseline_file_paths, [self.new_reports], '--resolved', 'json')

        print(resolved_results)

        self.assertFalse(resolved_results)
        self.assertEqual(returncode, 2)
        self.assertIn(
            "Couldn't get local reports for the following baseline report "
            "hashes: ",
            err)

    def test_print_bug_steps(self):
        """ Test printing the steps the analyzers took. """
        out, _, ret = get_diff_results(
            [self.base_reports], [self.new_reports], '--unresolved', None,
            ['--print-steps'])

        self.assertTrue("Steps:" in out)
        self.assertTrue("Report hash:" in out)
        self.assertEqual(ret, 2)
