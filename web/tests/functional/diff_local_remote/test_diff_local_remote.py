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
import sys
import unittest
import uuid

from libtest import codechecker
from libtest import env
from libtest import project
from libtest.codechecker import create_baseline_file, get_diff_results


class LocalRemote(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing diff_local_remote."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('diff_local_remote')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        test_project = 'cpp'

        project_info = project.get_info(test_project)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path_local = os.path.join(TEST_WORKSPACE, "test_proj_local")
        shutil.copytree(project.path(test_project), test_proj_path_local)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path_remote = os.path.join(TEST_WORKSPACE,
                                             "test_proj_remote")
        shutil.copytree(project.path(test_project), test_proj_path_remote)

        project_info['project_path_local'] = test_proj_path_local
        project_info['project_path_remote'] = test_proj_path_remote

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
            'analyzers': ['clangsa']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'diff_local_remote'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Analyze local, these reports will not be stored to the server.
        altered_file = os.path.join(test_proj_path_local,
                                    "call_and_message.cpp")
        project.insert_suppression(altered_file)

        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_local,
                                                    'reports')
        codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                       '-d', 'core.NullDereference']

        ret = codechecker.log_and_analyze(codechecker_cfg,
                                          test_proj_path_local)
        if ret:
            sys.exit(1)
        print('Analyzing local was successful.')

        # Store results to the remote server.
        test_project_name_remote = \
            project_info['name'] + '_' + uuid.uuid4().hex
        ret = codechecker.store(codechecker_cfg, test_project_name_remote)
        if ret:
            sys.exit(1)

        # Remote analysis, results will be stored to the remote server.
        altered_file = os.path.join(test_proj_path_local,
                                    "call_and_message.cpp")
        project.insert_suppression(altered_file)

        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_remote,
                                                    'reports')
        codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                       '-e', 'core.NullDereference']

        ret = codechecker.log_and_analyze(codechecker_cfg,
                                          test_proj_path_remote)
        if ret:
            sys.exit(1)
        print('Analyzing new was successful.')

        # Store results again to the remote server. We need this second store
        # to set the detection status to the required states.
        ret = codechecker.store(codechecker_cfg, test_project_name_remote)
        if ret:
            sys.exit(1)
        print('Analyzing remote was successful.')

        # Save the run names in the configuration.
        codechecker_cfg['run_names'] = [test_project_name_remote]

        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE, test_config)

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

    def get_local_remote_diff(self, extra_args=None, format_type=None):
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
                                '--unresolved', format_type,
                                ['--url', self._url, *extra_args])[0]

    def test_local_to_remote_compare_count_new(self):
        """Count the new results with no filter in local compare mode."""
        out, _, _ = get_diff_results([self._local_reports],
                                     [self._run_names[0]],
                                     '--new', None, ["--url", self._url])

        count = len(re.findall(r'\[core\.NullDereference\]', out))
        self.assertEqual(count, 4)

    def test_local_to_remote_unique_diff(self):
        """Check whether CodeChecker cmd diff crashes when --unique is on."""
        _, _, code = get_diff_results([self._local_reports],
                                      [self._run_names[0]],
                                      '--new', None,
                                      ["--url", self._url,
                                       "--uniqueing", "on"])

        self.assertEqual(code, 2)

    def test_remote_to_local_compare_count_new(self):
        """Count the new results with no filter."""
        out, _, _ = get_diff_results([self._run_names[0]],
                                     [self._local_reports],
                                     '--new', None, ["--url", self._url])

        # 5 new core.CallAndMessage issues.
        # 1 is suppressed in code
        count = len(re.findall(r'\[core\.CallAndMessage\]', out))
        self.assertEqual(count, 5)

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
        self.assertEqual(count, 11)
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
        self.assertEqual(count, 11)
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
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 19)

        res = self.get_local_remote_diff(['--severity', 'high', 'low'])
        self.assertEqual(len(re.findall(r'\[LOW\]', res)), 6)
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 19)

        res = self.get_local_remote_diff()
        self.assertEqual(len(re.findall(r'\[LOW\]', res)), 6)
        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 19)

    def test_local_cmp_filter_unres_filepath(self):
        """Filter unresolved results by file path."""
        res = self.get_local_remote_diff(['--file', '*divide_zero.cpp'])

        # Only 4 bugs can be found in the following file but in the
        # output the file names are printed again because of the summary.
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 6)

        self.assertEqual(len(re.findall(r'new_delete.cpp', res)), 0)

        res = self.get_local_remote_diff(['--file',
                                          'divide_zero.cpp',  # Exact match.
                                          '*new_delete.cpp'])
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 0)

        # Only 6 bugs can be found in the following file but in the
        # output the file names are printed again because of the summary.
        self.assertEqual(len(re.findall(r'new_delete.cpp', res)), 8)

    def test_local_cmp_filter_unres_checker_name(self):
        """Filter by checker name."""
        res = self.get_local_remote_diff(['--checker-name',
                                          'core.NullDereference'])
        self.assertEqual(len(re.findall(r'core.NullDereference', res)), 0)

        res = self.get_local_remote_diff(['--checker-name', 'core.*'])
        self.assertEqual(len(re.findall(r'core.*', res)), 16)

        # Filter by checker message (case insensitive).
        res = self.get_local_remote_diff(['--checker-msg', 'division by*'])
        self.assertEqual(len(re.findall(r'Division by.*', res)), 11)

    def test_local_cmp_filter_unres_filter_mix(self):
        """Filter by multiple filters file and severity."""
        res = self.get_local_remote_diff(['--file', '*divide_zero.cpp',
                                          '--severity', 'high'])

        # Only 2 bugs can be found in the following file but in the
        # output the file names are printed again because of the summary.
        self.assertEqual(len(re.findall(r'divide_zero.cpp', res)), 4)

        self.assertEqual(len(re.findall(r'\[HIGH\]', res)), 2)

    def test_local_cmp_filter_unres_filter_mix_json(self):
        """Filter by multiple filters file and severity with json output."""
        # TODO check if only high severity reports are retuned.
        reports = self.get_local_remote_diff(['--file', '*divide_zero.cpp',
                                              '--severity', 'high'], 'json')
        for report in reports:
            self.assertTrue("divide_zero.cpp" in report['file']['path'],
                            "Report filename is different from the expected.")

    def test_local_compare_res_html_output_unresolved(self):
        """Check that html files will be generated by using diff command."""
        html_reports = os.path.join(self._local_reports, "html_reports")

        get_diff_results([self._run_names[0]], [self._local_reports],
                         '--unresolved', 'html',
                         ["--url", self._url, '-e', html_reports,
                          "--verbose", "debug"])

        checked_files = set()
        for res in self.get_local_remote_diff(None, 'json'):
            checked_files.add(os.path.basename(res['file']['path']))

        # Check if index.html file was generated.
        html_index = os.path.join(html_reports, "index.html")
        self.assertTrue(os.path.exists(html_index))

        html_statistics = os.path.join(html_reports, "statistics.html")
        self.assertTrue(os.path.exists(html_statistics))

        # Check that html files were generated for each reports.
        for html_file_names in os.listdir(html_reports):
            suffix = html_file_names.rfind("_")
            file_name = html_file_names[:suffix] \
                if suffix != -1 else html_file_names

            if file_name in ["index.html", "statistics.html"]:
                continue

            self.assertIn(file_name, checked_files)

        # Check reports in the index.html file.
        index_html = os.path.join(html_reports, 'index.html')
        with open(index_html, 'r', encoding="utf-8", errors="ignore") as f:
            self.assertEqual(len(re.findall('core.DivideZero', f.read())), 11)

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

        environ = self._env.copy()
        environ["CC_REPO_DIR"] = ''
        environ["CC_CHANGED_FILES"] = ''

        get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--new', 'gerrit',
            ["--url", self._url, "-e", export_dir],
            environ)

        gerrit_review_file = os.path.join(export_dir, 'gerrit_review.json')
        self.assertTrue(os.path.exists(gerrit_review_file))

        with open(gerrit_review_file, 'r',
                  encoding="utf-8", errors="ignore") as rw_file:
            review_data = json.load(rw_file)

        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertEqual(review_data["message"],
                         "CodeChecker found 5 issue(s) in the code.")
        self.assertEqual(review_data["tag"], "jenkins")

        comments = review_data["comments"]
        self.assertEqual(len(comments), 1)

        file_path = next(iter(comments))
        reports = comments[file_path]
        self.assertEqual(len(reports), 5)
        for report in reports:
            self.assertIn("message", report)

            self.assertIn("range", report)
            report_range = report["range"]
            self.assertIn("start_line", report_range)
            self.assertIn("start_character", report_range)
            self.assertIn("end_line", report_range)
            self.assertIn("end_character", report_range)

        shutil.rmtree(export_dir, ignore_errors=True)

    def test_diff_gerrit_stdout(self):
        """Test gerrit stdout output.

        Only one output format was selected
        the gerrit review json should be printed to stdout.
        """
        environ = self._env.copy()
        environ["CC_REPO_DIR"] = ''
        environ["CC_CHANGED_FILES"] = ''

        review_data, _, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--new', 'gerrit',
            ["--url", self._url],
            environ)

        print(review_data)
        review_data = json.loads(review_data)
        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertEqual(review_data["message"],
                         "CodeChecker found 5 issue(s) in the code.")
        self.assertEqual(review_data["tag"], "jenkins")

        comments = review_data["comments"]
        self.assertEqual(len(comments), 1)

        file_path = next(iter(comments))
        reports = comments[file_path]
        self.assertEqual(len(reports), 5)
        for report in reports:
            self.assertIn("message", report)

            self.assertIn("range", report)
            report_range = report["range"]
            self.assertIn("start_line", report_range)
            self.assertIn("start_character", report_range)
            self.assertIn("end_line", report_range)
            self.assertIn("end_character", report_range)

    def test_set_env_diff_gerrit_output(self):
        """Test gerrit output when using diff and set env vars.

        Only the reports which belong to the changed files should
        be in the gerrit review json.
        """
        export_dir = os.path.join(self._local_reports, "export_dir2")

        environ = self._env.copy()
        environ["CC_REPO_DIR"] = self._local_test_project

        report_url = "localhost:8080/index.html"
        environ["CC_REPORT_URL"] = report_url

        changed_file_path = os.path.join(self._local_reports, 'files_changed')

        with open(changed_file_path, 'w',
                  encoding="utf-8", errors="ignore") as changed_file:
            # Print some garbage value to the file.
            changed_file.write(")]}'\n")

            changed_files = {
                "/COMMIT_MSG": {},
                "divide_zero.cpp": {}}
            changed_file.write(json.dumps(changed_files))

        environ["CC_CHANGED_FILES"] = changed_file_path

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
                         environ)

        gerrit_review_file = os.path.join(export_dir, 'gerrit_review.json')
        self.assertTrue(os.path.exists(gerrit_review_file))

        with open(gerrit_review_file, 'r',
                  encoding="utf-8", errors="ignore") as rw_file:
            review_data = json.load(rw_file)

        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertIn(
            "CodeChecker found 26 issue(s) in the code.",
            review_data["message"])
        self.assertIn(f"See: {report_url}", review_data["message"])
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

        environ = self._env.copy()
        environ["CC_REPO_DIR"] = self._local_test_project

        get_diff_results([self._run_names[0]], [self._local_reports],
                         '--unresolved', 'codeclimate',
                         ["--url", self._url, "-e", export_dir],
                         environ)

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

        div_zero_in_skip_h = [
            i for i in issues if
            i["fingerprint"] == "269d82a20d38f23bbf730a2cf1d1668b"]

        self.assertEqual(div_zero_in_skip_h, [{
            "type": "issue",
            "check_name": "core.DivideZero",
            "description": "Division by zero",
            "categories": [
                "Bug Risk"
            ],
            "fingerprint": "269d82a20d38f23bbf730a2cf1d1668b",
            "severity": "major",
            "location": {
                "path": "skip.h",
                "lines": {
                    "begin": 8
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
        self.assertTrue(file_path.endswith("/new_delete.cpp"))

        shutil.rmtree(export_dir_path, ignore_errors=True)

    def test_diff_multiple_output(self):
        """ Test multiple output type for diff command. """
        export_dir = os.path.join(self._local_reports, "export_dir3")

        environ = self._env.copy()
        environ["CC_REPO_DIR"] = ''
        environ["CC_CHANGED_FILES"] = ''

        out, _, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--resolved', None,
            ["-o", "html", "gerrit", "plaintext",
             "-e", export_dir,
             "--url", self._url],
            environ)

        print(out)
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

    def test_local_to_remote_with_baseline_file(self):
        """
        Get reports based on a baseline file given to the basename option.
        """
        baseline_file_path = create_baseline_file(self._local_reports)

        # Get new reports.
        new_results, _, returncode = get_diff_results(
            [baseline_file_path], [self._run_names[0]], '--new', 'json',
            ["--url", self._url])
        print(new_results)

        for report in new_results:
            self.assertEqual(report['checker_name'], "core.NullDereference")

        self.assertEqual(returncode, 2)

        # Get unresolved reports.
        unresolved_results, err, returncode = get_diff_results(
            [baseline_file_path], [self._run_names[0]], '--unresolved', 'json',
            ["--url", self._url])
        print(unresolved_results)

        self.assertTrue(unresolved_results)
        self.assertFalse(any(
            r for r in unresolved_results
            if r['checker_name'] == 'core.CallAndMessage'))
        self.assertEqual(returncode, 2)

        # Get resolved reports.
        resolved_results, err, returncode = get_diff_results(
            [baseline_file_path], [self._run_names[0]], '--resolved', 'json',
            ["--url", self._url])
        print(resolved_results)

        self.assertFalse(resolved_results)
        self.assertEqual(returncode, 2)
        self.assertIn(
            "Couldn't get local reports for the following baseline report "
            "hashes: ",
            err)

    def test_remote_to_local_with_baseline_file(self):
        """
        Get reports based on a baseline file given to the newname option.
        """
        baseline_file_path = create_baseline_file(self._local_reports)

        # Get new reports.
        res, _, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--new', 'json',
            ["--url", self._url,
             "--review-status", "unreviewed", "confirmed", "false_positive"])
        new_hashes = sorted(set(n['report_hash'] for n in res))

        new_results, err, returncode = get_diff_results(
            [self._run_names[0]], [baseline_file_path], '--new', 'json',
            ["--url", self._url])
        print(new_results)

        self.assertFalse(new_results)
        self.assertEqual(returncode, 2)
        self.assertIn(
            "Couldn't get local reports for the following baseline report "
            "hashes: " + ', '.join(new_hashes),
            err)

        # Get unresolved reports.
        res, _, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--unresolved', 'json',
            ["--url", self._url,
             "--review-status", "unreviewed", "confirmed", "false_positive"])
        unresolved_hashes = sorted(set(n['report_hash'] for n in res))

        unresolved_results, err, returncode = get_diff_results(
            [self._run_names[0]], [baseline_file_path],
            '--unresolved', 'json',
            ["--url", self._url])
        print(unresolved_results)

        self.assertFalse(unresolved_results)
        self.assertEqual(returncode, 2)
        self.assertIn(
            "Couldn't get local reports for the following baseline report "
            "hashes: " + ', '.join(unresolved_hashes),
            err)

        # Get resolved reports.
        res, _, _ = get_diff_results(
            [self._run_names[0]], [self._local_reports],
            '--resolved', 'json',
            ["--url", self._url,
             "--review-status", "unreviewed", "confirmed", "false_positive"])
        resolved_hashes = set(n['report_hash'] for n in res)

        resolved_results, _, returncode = get_diff_results(
            [self._run_names[0]], [baseline_file_path], '--resolved', 'json',
            ["--url", self._url,
             "--review-status", "unreviewed", "confirmed", "false_positive"])
        print(resolved_results)

        self.assertTrue(resolved_results)
        self.assertSetEqual(
            {r['report_hash'] for r in resolved_results}, resolved_hashes)
        self.assertEqual(returncode, 2)

    def test_print_bug_steps(self):
        """ Test printing the steps the analyzers took. """
        out, _, ret = get_diff_results(
            [self._run_names[0]], [self._local_reports], '--resolved', None,
            ["--url", self._url, "--print-steps"])

        self.assertTrue("Steps:" in out)
        self.assertTrue("Report hash:" in out)
        self.assertEqual(ret, 2)
