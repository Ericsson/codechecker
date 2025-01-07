# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""This module tests the CodeChecker 'analyze' and 'parse' feature."""


import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

from subprocess import CalledProcessError

from libtest import env
from libtest import project
from libtest.codechecker import call_command

from codechecker_report_converter.report import report_file
from codechecker_report_converter.report.output import baseline


class AnalyzeParseTestCaseMeta(type):

    def __new__(mcs, name, bases, test_dict):

        def gen_test(path, mode):
            """
            The returned test function will run the actual tests
            which compare the output of the command with the
            stored expected output.
            """

            def test(self):
                self.check_one_file(path, mode)
            return test

        test_dir = os.path.join(
            os.path.dirname(__file__), 'test_files')

        # Iterate over the test directory and generate the test cases
        # for each of the output files.
        for ofile in glob.glob(os.path.join(test_dir, '*.output')):
            test_name = 'test_' + os.path.basename(ofile)
            test_dict[test_name + '_normal'] = gen_test(ofile, 'NORMAL')
            test_dict[test_name + '_check'] = gen_test(ofile, 'CHECK')

        return type.__new__(mcs, name, bases, test_dict)


class AnalyzeParseTestCase(
        unittest.TestCase,
        metaclass=AnalyzeParseTestCaseMeta):
    """This class tests the CodeChecker 'analyze' and 'parse' feature."""

    @classmethod
    def setup_class(cls):
        """Setup the class."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('analyze_and_parse')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_workspace = os.environ['TEST_WORKSPACE']
        cls.test_workspaces = {'NORMAL': os.path.join(test_workspace,
                                                      'NORMAL'),
                               'CHECK': os.path.join(test_workspace,
                                                     'CHECK'),
                               'OUTPUT': os.path.join(test_workspace,
                                                      'OUTPUT')}

        # Get an environment with CodeChecker command in it.
        cls.env = env.codechecker_env()

        cls.test_dir = os.path.join(
            os.path.dirname(__file__), 'test_files')

        # Copy test projects and replace file path in plist files.
        test_projects = ['notes', 'macros']
        for test_project in test_projects:
            test_project_path = os.path.join(cls.test_workspaces['NORMAL'],
                                             "test_files", test_project)
            shutil.copytree(project.path(test_project), test_project_path)

            for test_file in os.listdir(test_project_path):
                if test_file.endswith(".plist"):
                    test_file_path = os.path.join(test_project_path, test_file)
                    with open(test_file_path, 'r+',
                              encoding="utf-8",
                              errors="ignore") as plist_file:
                        content = plist_file.read()
                        new_content = content.replace("$FILE_PATH$",
                                                      test_project_path)
                        plist_file.seek(0)
                        plist_file.truncate()
                        plist_file.write(new_content)

        # Change working dir to testfile dir so CodeChecker can be run easily.
        cls.__old_pwd = os.getcwd()
        os.chdir(cls.test_dir)

    @classmethod
    def teardown_class(cls):
        """Restore environment after tests have ran."""
        os.chdir(cls.__old_pwd)

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def teardown_method(self, _):
        """Restore environment after a particular test has run."""
        output_dir = AnalyzeParseTestCase.test_workspaces['OUTPUT']
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

    def __force_j1(self, cmd):
        """
        In case of CodeChecker analyze and check commands the analysis is
        forced to one core.
        """
        if cmd[1] != 'analyze' and cmd[1] != 'check':
            return cmd

        new_cmd = []

        i = 0
        while i < len(cmd):
            if cmd[i] == '-j' or cmd[i] == '--jobs':
                i += 2
            elif cmd[i].startswith('-j'):
                i += 1
            else:
                new_cmd.append(cmd[i])
                i += 1

        new_cmd.append('-j1')

        return new_cmd

    def check_one_file(self, path, mode):
        """
        Test 'analyze' and 'parse' output on a ".output" file.

        The '.output' file is formatted as follows:
          * >= 1 lines of CodeChecker commands to execute, prefixed by a 'mode'
            usually containing commands to build, log, analyze and parse the
            corresponding test file.
          * A single line containing some - (dashes)
          * The lines of the output which is expected to be produced by the
            commands in the lines above the -------------.

        mode specifies which command prefixes to execute.
        """
        with open(path, 'r', encoding="utf-8", errors="ignore") as ofile:
            lines = ofile.readlines()

        only_dash = re.compile(r'^[-]+$')
        dash_index = 0
        for idx, line in enumerate(lines):
            if re.match(only_dash, line):
                # The current line is the first line only containing dashes,
                # thus mark it as separator.
                dash_index = idx
                break

        commands = [line.strip() for line in lines[:dash_index]]
        current_commands = [c for c in commands if c.split('#')[0] == mode]
        if not current_commands:
            return

        correct_output = ''.join(lines[dash_index + 1:])

        run_name = os.path.basename(path).replace(".output", "")
        workspace = self.test_workspaces[mode]
        os.makedirs(os.path.join(workspace, run_name, "reports"))

        output = []
        for command in current_commands:
            split = command.split('#')
            command = ''.join(split[1:])

            command = command.replace("$LOGFILE$",
                                      os.path.join(workspace,
                                                   run_name, "build.json"))
            command = command.replace("$OUTPUT$",
                                      os.path.join(workspace,
                                                   run_name, "reports"))
            command = command.replace("$WORKSPACE$", workspace)

            try:
                result = subprocess.check_output(
                    self.__force_j1(shlex.split(command)),
                    env=self.env,
                    cwd=self.test_dir,
                    encoding="utf-8",
                    errors="ignore")

                output += result.splitlines(True)
            except CalledProcessError as cerr:
                output += cerr.output.splitlines(True)
                print("Failed to run: " + ' '.join(cerr.cmd))
                print(cerr.output)

        post_processed_output = []
        skip_prefixes = ["[] - Analysis length:",
                         "[] - Previous analysis results",
                         "[] - Skipping input file",
                         # Enabled checkers are listed in the beginning of
                         # analysis.
                         "[] - Enabled checker",
                         "clang-tidy:",
                         "clangsa:",
                         "cppcheck:",
                         "gcc:",
                         "infer:",
                         "Found 1 source file to analyze in"]
        for line in output:
            # replace timestamps
            line = re.sub(r'\[\w+ \d{4}-\d{2}-\d{2} \d{2}:\d{2}\]',
                          '[]', line)

            # Replace full path only to file name on the following
            # formatted lines:
            # 1.
            # [severity] /a/b/x.cpp:line:col: message [checker]
            # The replacement on this line will be the following:
            # [severity] x.cpp:line:col: message [checker]
            # 2.
            # [] - /a/b/x.cpp contains misspelled ...
            # The replacement on this line will be the following:
            # [] - x.cpp contains misspelled ...
            sep = re.escape(os.sep)
            line = re.sub(rf'^(\[\w+\]\s)(?P<path>.+{sep})'
                          r'(.+\:\d+\:\d+\:\s.*\s\[.*\])$',
                          r'\1\3', line)
            line = re.sub(rf'^\[\] - (?P<path>.+{sep})'
                          r'(.+ contains misspelled.+)',
                          r'[] - \2', line)

            if not any(line.startswith(prefix) for prefix in skip_prefixes):
                post_processed_output.append(line)

        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Actual output below:")
        print(''.join(post_processed_output))
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Expected output below:")
        print(correct_output)

        print("Test output file: " + path)
        self.maxDiff = None  # pylint: disable=invalid-name
        self.assertEqual(''.join(post_processed_output), correct_output)

    def test_json_output_for_macros(self):
        """ Test parse json output for macros. """
        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")

        extract_cmd = ['CodeChecker', 'parse', "-e", "json",
                       test_project_macros]

        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        res = json.loads(out)

        reports = res["reports"]
        self.assertEqual(len(reports), 1)
        res = reports[0]

        self.assertIn('checker_name', res)
        self.assertIn('report_hash', res)
        self.assertIn('file', res)

        self.assertIn('bug_path_events', res)
        self.assertTrue(res['bug_path_events'])

        self.assertIn('macro_expansions', res)
        self.assertTrue(res['macro_expansions'])

    def test_json_output_for_notes(self):
        """ Test parse json output for notes. """
        test_project_notes = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "notes")

        extract_cmd = ['CodeChecker', 'parse', "-e", "json",
                       test_project_notes]

        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        res = json.loads(out)

        reports = res["reports"]
        self.assertEqual(len(reports), 1)
        res = reports[0]

        self.assertIn('checker_name', res)
        self.assertIn('report_hash', res)
        self.assertIn('file', res)

        self.assertIn('bug_path_events', res)
        self.assertTrue(res['bug_path_events'])

        self.assertIn('notes', res)
        self.assertTrue(res['notes'])

    def test_codeclimate_output(self):
        """ Test parse codeclimate output. """
        test_project_notes = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "notes")
        extract_cmd = ['CodeChecker', 'parse', "-e", "codeclimate",
                       test_project_notes,
                       '--trim-path-prefix', test_project_notes]

        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        res = json.loads(out)

        self.assertEqual(res, [{
            'type': 'issue',
            'check_name': 'alpha.clone.CloneChecker',
            'description': 'Duplicate code detected',
            'categories': ['Bug Risk'],
            'fingerprint': '3d15184f38c5fa57e479b744fe3f5035',
            'severity': 'minor',
            'location': {
                'path': 'notes.cpp',
                'lines': {
                    'begin': 3
                }
            }
        }])

    def test_gerrit_output(self):
        """ Test gerrit output of the parse command. """

        environ = self.env.copy()
        report_url = "localhost:8080/index.html"
        environ["CC_REPORT_URL"] = report_url

        changed_file_path = os.path.join(self.test_dir, 'files_changed')

        with open(changed_file_path, 'w',
                  encoding="utf-8", errors="ignore") as changed_file:
            # Print some garbage value to the file.
            changed_file.write(")]}'\n")

            changed_files = {
                "/COMMIT_MSG": {},
                "macros.cpp": {}}
            changed_file.write(json.dumps(changed_files))

        environ["CC_CHANGED_FILES"] = changed_file_path

        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")
        environ["CC_REPO_DIR"] = test_project_macros

        extract_cmd = ['CodeChecker', 'parse', test_project_macros,
                       '-e', 'gerrit']

        print(" ".join(extract_cmd))
        out, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=environ)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        print(out)

        review_data = json.loads(out)

        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertEqual(review_data["message"],
                         "CodeChecker found 1 issue(s) in the code. "
                         f"See: {report_url}")
        self.assertEqual(review_data["tag"], "jenkins")

        # Because the CC_CHANGED_FILES is set we will see reports only for
        # the macro.cpp file.
        comments = review_data["comments"]
        self.assertEqual(len(comments), 1)

        reports = comments["macros.cpp"]
        self.assertEqual(len(reports), 1)

        os.remove(changed_file_path)

    def test_invalid_plist_file(self):
        """ Test parsing invalid plist file. """
        invalid_plist_file = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "invalid.plist")
        with open(invalid_plist_file, "w+",
                  encoding="utf-8",
                  errors="ignore") as invalid_plist_f:
            invalid_plist_f.write("Invalid plist file.")

        extract_cmd = ['CodeChecker', 'parse', invalid_plist_file]

        out, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 0, "Parsing failed.")
        self.assertTrue("Invalid plist file" in out)

    def test_html_output_for_macros(self):
        """ Test parse HTML output for macros. """
        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")

        output_path = os.path.join(self.test_workspaces['OUTPUT'], 'html')
        extract_cmd = ['CodeChecker', 'parse',
                       '-e', 'html',
                       '-o', output_path,
                       test_project_macros]

        out, err, result = call_command(extract_cmd, cwd=self.test_dir,
                                        env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        self.assertFalse(err)

        self.assertTrue('Html file was generated' in out)
        self.assertTrue('Summary' in out)
        self.assertTrue('Statistics' in out)

    def test_html_output_for_empty_dir(self):
        """ Test parse HTML output for an empty directory. """
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(self.test_workspaces['OUTPUT'], 'html')
            extract_cmd = [
                'CodeChecker', 'parse',
                '-e', 'html',
                '-o', output_path,
                tmp_dir]

            out, err, result = call_command(
                extract_cmd, cwd=self.test_dir, env=self.env)
            self.assertEqual(result, 0)
            self.assertFalse(err)

            self.assertTrue('Summary' in out)
            self.assertFalse('Html file was generated' in out)
            self.assertFalse('Statistics' in out)

    def test_codeclimate_export(self):
        """ Test exporting codeclimate output. """
        test_project_notes = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "notes")
        output_file_path = os.path.join(
            self.test_workspaces['OUTPUT'], 'reports.json')
        extract_cmd = ['CodeChecker', 'parse', "--export", "codeclimate",
                       test_project_notes, "--output", output_file_path,
                       '--trim-path-prefix', test_project_notes]

        _, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                    env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")

        with open(output_file_path, 'r', encoding='utf-8', errors='ignore') \
                as f:
            results = json.load(f)

        self.assertTrue(results)

    def test_codeclimate_export_exit_code_when_all_skipped(self):
        """ Test exporting codeclimate output into the filesystem when all
            bug are skipped.
        """
        test_project_notes = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "notes")
        skip_file_path = os.path.join(self.test_dir, 'skipall.txt')
        extract_cmd = ['CodeChecker', 'parse', "--export", "codeclimate",
                       test_project_notes, "--skip", skip_file_path,
                       '--trim-path-prefix', test_project_notes]

        standard_output, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 0, "Parsing should not found any issue.")
        self.assertEqual("[]\n", standard_output,
                         "Result should be an empty json array.")

    def test_gerrit_export_exit_code_when_all_skipped(self):
        """ Test exporting gerrit output into the filesystem when all bug
            are skipped.
        """

        environ = self.env.copy()
        report_url = "localhost:8080/index.html"
        environ["CC_REPORT_URL"] = report_url

        changed_file_path = os.path.join(self.test_dir, 'files_changed')

        with open(changed_file_path, 'w',
                  encoding="utf-8", errors="ignore") as changed_file:
            # Print some garbage value to the file.
            changed_file.write(")]}'\n")

            changed_files = {
                "/COMMIT_MSG": {},
                "macros.cpp": {}}
            changed_file.write(json.dumps(changed_files))

        environ["CC_CHANGED_FILES"] = changed_file_path

        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")
        environ["CC_REPO_DIR"] = test_project_macros
        skip_file_path = os.path.join(self.test_dir, 'skipall.txt')

        extract_cmd = ['CodeChecker', 'parse', test_project_macros,
                       '--export', 'gerrit', '--skip', skip_file_path]

        print(" ".join(extract_cmd))
        standard_output, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=environ)
        os.remove(changed_file_path)
        self.assertEqual(result, 0, "Parsing should not found any issue.")
        self.assertIn(
            "CodeChecker found 0 issue(s) in the code.", standard_output,
            "Result should not found any issue.")

    def test_json_export_exit_code_when_all_skipped(self):
        """ Test exporting gerrit output into the filesystem when all bug
            are skipped.
        """
        test_project_notes = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "notes")
        skip_file_path = os.path.join(self.test_dir, 'skipall.txt')
        extract_cmd = ['CodeChecker', 'parse', "--export", "json",
                       test_project_notes, "--skip", skip_file_path,
                       '--trim-path-prefix', test_project_notes]

        standard_output, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 0, "Parsing should not found any issue.")

        data = json.loads(standard_output)
        self.assertEqual(data["version"], 1)
        self.assertFalse(data["reports"])

    def test_parse_exit_code(self):
        """ Test exit code of parsing. """
        test_project_notes = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "notes")
        extract_cmd = ['CodeChecker', 'parse',
                       test_project_notes, '--trim-path-prefix',
                       test_project_notes]
        _, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                    env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        skip_file_path = os.path.join(self.test_dir, 'skipall.txt')
        extract_cmd.extend(["--skip", skip_file_path])
        _, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                    env=self.env)
        self.assertEqual(result, 0, "Parsing should not found any issue.")

    def test_html_export_exit_code(self):
        """ Test exit code while HTML output generation. """
        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")

        extract_cmd = ['CodeChecker', 'parse', '--export', 'html',
                       test_project_macros]
        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
        self.assertEqual(result, 1, "HTML parsing requires output directory.")
        self.assertTrue("export not allowed without argument" in out)

        output_path = os.path.join(self.test_workspaces['OUTPUT'], 'html')
        extract_cmd.extend(['--output', output_path])
        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        self.assertTrue('Html file was generated' in out)
        self.assertTrue('Summary' in out)
        self.assertTrue('Statistics' in out)

        skip_file_path = os.path.join(self.test_dir, 'skipall.txt')
        extract_cmd.extend(["--skip", skip_file_path])
        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
        self.assertEqual(result, 0, "Parsing should not found any issue.")

    def test_baseline_output(self):
        """ Test parse baseline output. """
        output_path = self.test_workspaces['OUTPUT']
        out_file_path = os.path.join(output_path, "reports.baseline")

        # Analyze the first project.
        test_project_notes = os.path.join(
            self.test_workspaces['NORMAL'], "test_files", "notes")

        extract_cmd = ['CodeChecker', 'parse',
                       "-e", "baseline",
                       "-o", out_file_path,
                       test_project_notes,
                       '--trim-path-prefix', test_project_notes]

        _, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")

        report_hashes = baseline.get_report_hashes([out_file_path])
        self.assertEqual(
            report_hashes, {'3d15184f38c5fa57e479b744fe3f5035'})

        # Analyze the second project and see whether the baseline file is
        # merged.
        test_project_macros = os.path.join(
            self.test_workspaces['NORMAL'], "test_files", "macros")

        extract_cmd = ['CodeChecker', 'parse',
                       "-e", "baseline",
                       "-o", out_file_path,
                       test_project_macros,
                       '--trim-path-prefix', test_project_macros]

        _, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")

        report_hashes = baseline.get_report_hashes([out_file_path])
        self.assertSetEqual(report_hashes, {
            '3d15184f38c5fa57e479b744fe3f5035',
            'f8fbc46cc5afbb056d92bd3d3d702781'})

    def test_invalid_baseline_file_extension(self):
        """ Test invalid baseline file extension for parse. """
        output_path = self.test_workspaces['OUTPUT']
        out_file_path = os.path.join(output_path, "cc_reports.invalid")

        # Analyze the first project.
        test_project_notes = os.path.join(
            self.test_workspaces['NORMAL'], "test_files", "notes")

        # Try to create baseline file with invalid extension.
        parse_cmd = [
            "CodeChecker", "parse", "-e", "baseline", "-o", out_file_path,
            test_project_notes]

        _, err, result = call_command(
            parse_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 1)
        self.assertIn("Baseline files must have '.baseline' extensions", err)

        # Try to create baseline file in a directory which exists.
        os.makedirs(output_path)
        parse_cmd = [
            "CodeChecker", "parse", "-e", "baseline", "-o", output_path,
            test_project_notes]

        _, err, result = call_command(
            parse_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 1)
        self.assertIn("Please provide a file path instead of a directory", err)

    def test_custom_baseline_file(self):
        """ Test parse baseline custom output file. """
        output_path = self.test_workspaces['OUTPUT']
        out_file_path = os.path.join(output_path, "cc_reports.baseline")

        # Analyze the first project.
        test_project_notes = os.path.join(
            self.test_workspaces['NORMAL'], "test_files", "notes")

        extract_cmd = ['CodeChecker', 'parse',
                       "-e", "baseline",
                       "-o", out_file_path,
                       test_project_notes]

        _, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")

        report_hashes = baseline.get_report_hashes([out_file_path])
        self.assertEqual(
            report_hashes, {'3d15184f38c5fa57e479b744fe3f5035'})

    def test_html_output_for_empty_plist(self):
        """
        Test that HTML files for empty plist files will not be generated.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            plist_file_name = 'empty.plist'
            plist_file_path = os.path.join(tmp_dir, plist_file_name)
            report_file.create(plist_file_path, [])

            test_project_notes = os.path.join(
                self.test_workspaces['NORMAL'], "test_files", "notes",
                "notes.plist")
            shutil.copy(test_project_notes, tmp_dir)

            output_path = os.path.join(tmp_dir, 'html')
            extract_cmd = [
                'CodeChecker', 'parse',
                '-e', 'html',
                '-o', output_path,
                tmp_dir]

            out, err, result = call_command(
                extract_cmd, cwd=self.test_dir, env=self.env)

            self.assertEqual(result, 2)
            self.assertFalse(err)

            self.assertTrue(f'No report data in {plist_file_path}' in out)
            self.assertTrue('Html file was generated:' in out)
            self.assertTrue('Summary' in out)
            self.assertTrue('statistics.html' in out)
            self.assertTrue('index.html' in out)

            self.assertTrue(os.path.exists(
                os.path.join(output_path, 'index.html')))
            self.assertTrue(os.path.exists(
                os.path.join(output_path, 'statistics.html')))
            self.assertTrue(os.path.exists(
                os.path.join(output_path, 'notes.plist.html')))
            self.assertFalse(os.path.exists(
                os.path.join(output_path, f'{plist_file_name}.html')))

    def test_html_checker_url(self):
        """ Test whether checker documentation urls are generated properly. """
        with tempfile.TemporaryDirectory() as tmp_dir:
            notes_plist = os.path.join(
                self.test_workspaces['NORMAL'], "test_files", "notes",
                "notes.plist")
            macros_plist = os.path.join(
                self.test_workspaces['NORMAL'], "test_files", "macros",
                "macros.plist")
            shutil.copy(notes_plist, tmp_dir)
            shutil.copy(macros_plist, tmp_dir)

            macros_plist = os.path.join(tmp_dir, 'macros.plist')
            with open(macros_plist, 'r+',
                      encoding="utf-8", errors="ignore") as f:
                content = f.read()
                new_content = content.replace(
                    "core.NullDereference", "UNKNOWN CHECKER NAME")
                f.seek(0)
                f.truncate()
                f.write(new_content)

            output_path = os.path.join(tmp_dir, 'html')
            extract_cmd = [
                'CodeChecker', 'parse', '-e', 'html', '-o', output_path,
                tmp_dir]

            _, err, result = call_command(extract_cmd, cwd=self.test_dir,
                                          env=self.env)
            self.assertEqual(result, 2, "Parsing not found any issue.")
            self.assertFalse(err)

            # Test whether documentation urls are set properly for known
            # checkers in the index.html file.
            index_html = os.path.join(output_path, "index.html")
            with open(index_html, 'r', encoding="utf-8", errors="ignore") as f:
                content = f.read()

            self.assertTrue(re.search(
                '"checker-url": ".*alpha-clone-clonechecker', content))
            self.assertTrue(re.search('"checker-url": ""', content))
            self.assertTrue(re.search('UNKNOWN CHECKER NAME', content))

            # Test whether documentation urls are set properly for known
            # checkers in the generated HTML report file.
            report_html = os.path.join(output_path, "notes.plist.html")
            with open(report_html, 'r',
                      encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.assertTrue(re.search('"url": ".+"', content))

            # Test whether documentation urls are not set for unknown checkers
            # in the generated HTML report file.
            report_html = os.path.join(output_path, "macros.plist.html")
            with open(report_html, 'r',
                      encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.assertTrue(re.search('"url": ""', content))

    def test_mixed_architecture_logging(self):
        """
        Test if CodeChecker can properly log compilation commands when the
        build process involves both 32-bit and 64-bit binaries acting as
        build drivers.

        This verifies that the LD_LIBRARY_PATH setup in analyzer_context.py
        correctly includes all architecture versions of the ld_logger.so
        library, and that logging works with this setup.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # We use a temporary directory, because we produce multiple files
            # during this test, and it is easier to clean up.
            mixed_arch_driver = os.path.join(
                self.test_dir,
                "mixed_arch_driver.c"
            )
            simple_c = os.path.join(
                self.test_dir,
                "simple.c"
            )

            shutil.copy(mixed_arch_driver, tmp_dir)
            shutil.copy(simple_c, tmp_dir)

            best_gcc_candidate_in_path = [
                path
                for path in os.environ["PATH"].split(":")
                if os.path.exists(os.path.join(path, "gcc"))
            ]
            if not best_gcc_candidate_in_path:
                self.skipTest(f"No gcc candidate found in PATH:\
                              {os.environ['PATH']}")

            try:
                subprocess.check_call(
                    ["gcc", "-m32", "-c", "simple.c"],
                    cwd=tmp_dir,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as err:
                self.skipTest(f"No 32-bit compilation support available:\
                              {err.stderr}")
            try:
                subprocess.check_call(
                    ["gcc", "-m64", "-c", "simple.c"],
                    cwd=tmp_dir,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as err:
                self.skipTest(f"No 64-bit compilation support available:\
                              {err.stderr}")

            subprocess.check_call(
                ["gcc", "-m32", "mixed_arch_driver.c", "-o", "driver32"],
                cwd=tmp_dir
            )
            subprocess.check_call(
                ["gcc", "-m64", "mixed_arch_driver.c", "-o", "driver64"],
                cwd=tmp_dir
            )

            log_file = os.path.join(tmp_dir, "compile_commands.json")
            cmd = [
                "CodeChecker", "log", "-b", "./driver32;./driver64",
                "-o", log_file,
            ]

            _, err, returncode = call_command(cmd, cwd=tmp_dir,
                                              env=self.env)

            self.assertEqual(returncode, 0, f"CodeChecker log failed:\
                             {err}")

            # Verify the logged commands
            with open(log_file, "r", encoding="utf-8") as f:
                logged_commands = json.load(f)

            # The buildlog should have 4 commands - 2 from each driver
            # (and for each driver there is one with a '-m32' and one with a
            # '-m64' flag)
            self.assertEqual(
                len(logged_commands), 4, f"Logged commands: {logged_commands}"
            )

            commands = [entry["command"] for entry in logged_commands]
            self.assertTrue(
                2 == len([cmd for cmd in commands if "-m32" in cmd]),
                f"Expected 2 32-bit compilations. Logged commands:\
                 {logged_commands}"
            )
            self.assertTrue(
                2 == len([cmd for cmd in commands if "-m64" in cmd]),
                f"Expected 2 64-bit compilations. Logged commands:\
                 {logged_commands}"
            )
