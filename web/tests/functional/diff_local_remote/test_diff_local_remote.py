#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""diff_local_remote function test.

Tests for the diff feature when comparing a local report directory
with a remote run in the database.
"""


import json
import os
import re
import shutil
import subprocess
import unittest

from libtest import env
from libtest.codechecker import get_diff_results


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

        self._local_test_project = \
            self._test_cfg['test_project']['project_path_local']
        self._remote_test_project = \
            self._test_cfg['test_project']['project_path_remote']

        self._local_reports = os.path.join(self._local_test_project,
                                           'reports')
        self._remote_reports = os.path.join(self._remote_test_project,
                                            'reports')

        self._url = env.parts_to_url(self._test_cfg['codechecker_cfg'])

        self._env = self._test_cfg['codechecker_cfg']['check_env']

    def get_local_remote_diff(self, extra_args=None):
        """Return the unresolved results comparing local to a remote.

        Returns the text output of the diff command comparing the
        local reports to a remote run in the database.

        extra_args: can be used to add list of additional
                    arguments to the diff command.
                    Like filter arguments or to change output format.
        """
        if not extra_args:
            extra_args = []

        return get_diff_results([self._local_reports], [self._run_names[0]],
                                '--unresolved', None,
                                ['--url', self._url, *extra_args])[0]

    def test_local_to_remote_compare_count_new(self):
        """Count the new results with no filter in local compare mode."""
        out, _, _ = get_diff_results([self._local_reports],
                                     [self._run_names[0]],
                                     '--new', None, ["--url", self._url])

        count = len(re.findall(r'\[core\.NullDereference\]', out))
        self.assertEqual(count, 4)

    def test_remote_to_local_compare_count_new(self):
        """Count the new results with no filter."""
        out, _, _ = get_diff_results([self._run_names[0]],
                                     [self._local_reports],
                                     '--new', None, ["--url", self._url])

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
        out, _, _ = get_diff_results(
            [self._local_reports], [self._run_names[0]],
            '--unresolved', None, ["--url", self._url])
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
        out, _, _ = get_diff_results(
            [self._local_reports], [self._run_names[0]],
            '--unresolved', None, ["--url", self._url])
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

        # Only 4 bugs can be found in the following file but in the
        # output the file names are printed again because of the summary.
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 5)

        self.assertEqual(len(re.findall(r'new_delete.cpp', res)), 0)

        res = self.get_local_remote_diff(['--file',
                                          'divide_zero.cpp',  # Exact match.
                                          '*new_delete.cpp'])
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 0)

        # Only 6 bugs can be found in the following file but in the
        # output the file names are printed again because of the summary.
        self.assertEqual(len(re.findall(r'new_delete.cpp', res)), 7)

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

        # Only 2 bugs can be found in the following file but in the
        # output the file names are printed again because of the summary.
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 3)

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
        html_reports = os.path.join(self._local_reports, "html_reports")

        get_diff_results([self._run_names[0]], [self._local_reports],
                         '--unresolved', 'html',
                         ["--url", self._url, '-e', html_reports,
                          "--verbose", "debug"])

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

    def test_different_basename_types(self):
        """ Test different basename types.

        Test that diff command will fail when remote run and local report
        directory are given to the basename parameter.
        """
        base_run_name = self._run_names[0]

        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "-b", base_run_name, self._local_reports,
                    "-n", self._local_reports,
                    "--unresolved",
                    "--url", self._url]

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output(
                diff_cmd,
                env=self._env,
                cwd=os.environ['TEST_WORKSPACE'],
                encoding="utf-8",
                errors="ignore")

    def test_different_newname_types(self):
        """ Test different newname types.

        Test that diff command will fail when remote run and local report
        directory are given to the newname parameter.
        """
        base_run_name = self._run_names[0]

        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "-b", base_run_name,
                    "-n", self._local_reports, base_run_name,
                    "--unresolved",
                    "--url", self._url]

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output(
                diff_cmd,
                env=self._env,
                cwd=os.environ['TEST_WORKSPACE'],
                encoding="utf-8",
                errors="ignore")

    def test_diff_gerrit_output(self):
        """Test gerrit output.

        Every report should be in the gerrit review json.
        """
        export_dir = os.path.join(self._local_reports, "export_dir1")

        env = self._env.copy()
        env["CC_REPO_DIR"] = ''
        env["CC_CHANGED_FILES"] = ''

        get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--new', 'gerrit',
            ["--url", self._url, "-e", export_dir],
            env)

        gerrit_review_file = os.path.join(export_dir, 'gerrit_review.json')
        self.assertTrue(os.path.exists(gerrit_review_file))

        with open(gerrit_review_file, 'r',
                  encoding="utf-8", errors="ignore") as rw_file:
            review_data = json.load(rw_file)

        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertEqual(review_data["message"],
                         "CodeChecker found 4 issue(s) in the code.")
        self.assertEqual(review_data["tag"], "jenkins")

        comments = review_data["comments"]
        self.assertEqual(len(comments), 1)

        file_path = next(iter(comments))
        reports = comments[file_path]
        self.assertEqual(len(reports), 4)
        for report in reports:
            self.assertIn("message", report)

            self.assertIn("range", report)
            range = report["range"]
            self.assertIn("start_line", range)
            self.assertIn("start_character", range)
            self.assertIn("end_line", range)
            self.assertIn("end_character", range)

        shutil.rmtree(export_dir, ignore_errors=True)

    def test_diff_gerrit_stdout(self):
        """Test gerrit stdout output.

        Only one output format was selected
        the gerrit review json should be printed to stdout.
        """
        env = self._env.copy()
        env["CC_REPO_DIR"] = ''
        env["CC_CHANGED_FILES"] = ''

        review_data, _, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--new', 'gerrit',
            ["--url", self._url],
            env)

        print(review_data)
        review_data = json.loads(review_data)
        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertEqual(review_data["message"],
                         "CodeChecker found 4 issue(s) in the code.")
        self.assertEqual(review_data["tag"], "jenkins")

        comments = review_data["comments"]
        self.assertEqual(len(comments), 1)

        file_path = next(iter(comments))
        reports = comments[file_path]
        self.assertEqual(len(reports), 4)
        for report in reports:
            self.assertIn("message", report)

            self.assertIn("range", report)
            range = report["range"]
            self.assertIn("start_line", range)
            self.assertIn("start_character", range)
            self.assertIn("end_line", range)
            self.assertIn("end_character", range)

    def test_set_env_diff_gerrit_output(self):
        """Test gerrit output when using diff and set env vars.

        Only the reports which belong to the changed files should
        be in the gerrit review json.
        """
        export_dir = os.path.join(self._local_reports, "export_dir2")

        env = self._env.copy()
        env["CC_REPO_DIR"] = self._local_test_project

        report_url = "localhost:8080/index.html"
        env["CC_REPORT_URL"] = report_url

        changed_file_path = os.path.join(self._local_reports, 'files_changed')

        with open(changed_file_path, 'w',
                  encoding="utf-8", errors="ignore") as changed_file:
            # Print some garbage value to the file.
            changed_file.write(")]}'\n")

            changed_files = {
                "/COMMIT_MSG": {},
                "divide_zero.cpp": {}}
            changed_file.write(json.dumps(changed_files))

        env["CC_CHANGED_FILES"] = changed_file_path

        _, err, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--unresolved', 'gerrit',
            ["--url", self._url, "-e", export_dir])

        self.assertIn("'CC_REPO_DIR'", err)
        self.assertIn("'CC_CHANGED_FILES'", err)
        self.assertIn("needs to be set", err)

        get_diff_results([self._run_names[0]], [self._local_reports],
                         '--unresolved', 'gerrit',
                         ["--url", self._url, "-e", export_dir],
                         env)

        gerrit_review_file = os.path.join(export_dir, 'gerrit_review.json')
        self.assertTrue(os.path.exists(gerrit_review_file))

        with open(gerrit_review_file, 'r',
                  encoding="utf-8", errors="ignore") as rw_file:
            review_data = json.load(rw_file)

        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertIn(
            "CodeChecker found 25 issue(s) in the code.",
            review_data["message"])
        self.assertIn(f"See: '{report_url}'", review_data["message"])
        self.assertEqual(review_data["tag"], "jenkins")

        # Because the CC_CHANGED_FILES is set we will see reports only for
        # the divide_zero.cpp function in the comments section.
        comments = review_data["comments"]
        self.assertEqual(len(comments), 1)

        reports = comments["divide_zero.cpp"]
        self.assertEqual(len(reports), 4)

        shutil.rmtree(export_dir, ignore_errors=True)

    def test_diff_codeclimate_output(self):
        """ Test codeclimate output when using diff and set env vars. """
        export_dir = os.path.join(self._local_reports, "export_dir")

        env = self._env.copy()
        env["CC_REPO_DIR"] = self._local_test_project

        get_diff_results([self._run_names[0]], [self._local_reports],
                         '--unresolved', 'codeclimate',
                         ["--url", self._url, "-e", export_dir],
                         env)

        codeclimate_issues_file = os.path.join(export_dir,
                                               'codeclimate_issues.json')
        self.assertTrue(os.path.exists(codeclimate_issues_file))

        with open(codeclimate_issues_file, 'r',
                  encoding="utf-8", errors="ignore") as rw_file:
            issues = json.load(rw_file)

        for issue in issues:
            self.assertEqual(issue["type"], "issue")
            self.assertTrue(issue["check_name"])
            self.assertEqual(issue["categories"], ["Bug Risk"])
            self.assertTrue(issue["fingerprint"])
            self.assertTrue(issue["location"]["path"])
            self.assertTrue(issue["location"]["lines"]["begin"])

        malloc_issues = [i for i in issues if i["check_name"] == "unix.Malloc"]
        self.assertEqual(malloc_issues, [{
            "type": "issue",
            "check_name": "unix.Malloc",
            "description": "Memory allocated by alloca() should not be "
                           "deallocated",
            "categories": [
                "Bug Risk"
            ],
            "fingerprint": "c2132f78ef0e01bdb5eacf616048625f",
            "severity": "minor",
            "location": {
                "path": "new_delete.cpp",
                "lines": {
                    "begin": 31
                }
            }}])

        shutil.rmtree(export_dir, ignore_errors=True)

    def test_diff_no_trim_codeclimate_output(self):
        """ Test codeclimate output when using diff and don't set env vars. """
        export_dir_path = os.path.join(self._local_reports, "export_dir")

        get_diff_results([self._run_names[0]], [self._local_reports],
                         '--unresolved', "codeclimate",
                         ["-e", export_dir_path, "--url", self._url],
                         self._env)

        issues_file_path = os.path.join(export_dir_path,
                                        'codeclimate_issues.json')
        self.assertTrue(os.path.exists(issues_file_path))

        with open(issues_file_path, 'r',
                  encoding="utf-8", errors="ignore") as f:
            issues = json.load(f)

        malloc_issues = [i for i in issues if i["check_name"] == "unix.Malloc"]
        self.assertNotEqual(len(malloc_issues), 0)

        file_path = malloc_issues[0]["location"]["path"]
        self.assertTrue(os.path.isabs(file_path))
        self.assertTrue(file_path.endswith(f"/new_delete.cpp"))

        shutil.rmtree(export_dir_path, ignore_errors=True)

    def test_diff_multiple_output(self):
        """ Test multiple output type for diff command. """
        export_dir = os.path.join(self._local_reports, "export_dir3")

        env = self._env.copy()
        env["CC_REPO_DIR"] = ''
        env["CC_CHANGED_FILES"] = ''

        out, _, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--resolved', None,
            ["-o", "html", "gerrit", "plaintext",
             "-e", export_dir,
             "--url", self._url],
            env)

        # Check the plaintext output.
        count = len(re.findall(r'\[core\.NullDereference\]', out))
        self.assertEqual(count, 4)

        # Check that the gerrit output json file was generated.
        gerrit_review_file = os.path.join(export_dir, 'gerrit_review.json')
        self.assertTrue(os.path.exists(gerrit_review_file))

        # Check that index.html output was generated.
        index_html = os.path.join(export_dir, 'index.html')
        self.assertTrue(os.path.exists(index_html))

        shutil.rmtree(export_dir, ignore_errors=True)

    def test_diff_remote_local_resolved_same(self):
        """ Test for resolved reports on same list remotely and locally. """
        out, _, _ = get_diff_results(
            [self._run_names[0]], [self._remote_reports],
            '--resolved', 'json', ["--url", self._url])
        self.assertEqual(out, [])
