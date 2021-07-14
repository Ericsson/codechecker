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
import unittest

from subprocess import CalledProcessError

from libtest import env
from libtest import project
from libtest.codechecker import call_command


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

        # TEST_WORKSPACE is automatically set by test package __init__.py
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

    def tearDown(self):
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
                         "[] - Enabled checkers:",
                         "clang-tidy:",
                         "clangsa:"]
        for line in output:
            # replace timestamps
            line = re.sub(r'\[\w+ \d{4}-\d{2}-\d{2} \d{2}:\d{2}\]',
                          '[]', line)

            # Replace full path only to file name on the following
            # formatted lines:
            # [severity] /a/b/x.cpp:line:col: message [checker]
            # The replacement on this line will be the following:
            # [severity] x.cpp:line:col: message [checker]
            sep = re.escape(os.sep)
            line = re.sub(r'^(\[\w+\]\s)(?P<path>.+{0})'
                          r'(.+\:\d+\:\d+\:\s.*\s\[.*\])$'.format(sep),
                          r'\1\3', line)

            if not any([line.startswith(prefix) for prefix
                        in skip_prefixes]):
                post_processed_output.append(line)

        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Actual output below:")
        print(''.join(post_processed_output))
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Expected output below:")
        print(correct_output)

        print("Test output file: " + path)
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

        self.assertEqual(len(res), 1)
        res = res[0]

        self.assertIn('check_name', res)
        self.assertIn('issue_hash_content_of_line_in_context', res)

        self.assertIn('files', res)
        self.assertEqual(len(res['files']), 1)

        self.assertIn('path', res)
        self.assertTrue(res['path'])

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

        self.assertEqual(len(res), 1)
        res = res[0]

        self.assertIn('check_name', res)
        self.assertIn('issue_hash_content_of_line_in_context', res)

        self.assertIn('files', res)
        self.assertEqual(len(res['files']), 1)

        self.assertIn('path', res)
        self.assertTrue(res['path'])

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

        env = self.env.copy()
        report_url = "localhost:8080/index.html"
        env["CC_REPORT_URL"] = report_url

        changed_file_path = os.path.join(self.test_dir, 'files_changed')

        with open(changed_file_path, 'w',
                  encoding="utf-8", errors="ignore") as changed_file:
            # Print some garbage value to the file.
            changed_file.write(")]}'\n")

            changed_files = {
                "/COMMIT_MSG": {},
                "macros.cpp": {}}
            changed_file.write(json.dumps(changed_files))

        env["CC_CHANGED_FILES"] = changed_file_path

        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")
        env["CC_REPO_DIR"] = test_project_macros

        extract_cmd = ['CodeChecker', 'parse', test_project_macros,
                       '-e', 'gerrit']

        print(" ".join(extract_cmd))
        out, _, result = call_command(extract_cmd, cwd=self.test_dir, env=env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        print(out)

        review_data = json.loads(out)

        lbls = review_data["labels"]
        self.assertEqual(lbls["Verified"], -1)
        self.assertEqual(lbls["Code-Review"], -1)
        self.assertEqual(review_data["message"],
                         "CodeChecker found 1 issue(s) in the code. "
                         "See: '{0}'".format(report_url))
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

        extract_cmd = ['CodeChecker', 'parse',
                       invalid_plist_file]

        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
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

    def test_codeclimate_export(self):
        """ Test exporting codeclimate output. """
        test_project_notes = os.path.join(self.test_workspaces['NORMAL'],
                                          "test_files", "notes")
        output_path = self.test_workspaces['OUTPUT']
        extract_cmd = ['CodeChecker', 'parse', "--export", "codeclimate",
                       test_project_notes, "--output", output_path,
                       '--trim-path-prefix', test_project_notes]

        out, _, result = call_command(extract_cmd, cwd=self.test_dir,
                                      env=self.env)
        self.assertEqual(result, 2, "Parsing not found any issue.")
        result_from_stdout = json.loads(out)
        output_file_path = os.path.join(output_path, "reports.json")
        with open(output_file_path, 'r', encoding='utf-8', errors='ignore') \
                as handle:
            result_from_file = json.load(handle)

        self.assertEqual(result_from_stdout, result_from_file)

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

        env = self.env.copy()
        report_url = "localhost:8080/index.html"
        env["CC_REPORT_URL"] = report_url

        changed_file_path = os.path.join(self.test_dir, 'files_changed')

        with open(changed_file_path, 'w',
                  encoding="utf-8", errors="ignore") as changed_file:
            # Print some garbage value to the file.
            changed_file.write(")]}'\n")

            changed_files = {
                "/COMMIT_MSG": {},
                "macros.cpp": {}}
            changed_file.write(json.dumps(changed_files))

        env["CC_CHANGED_FILES"] = changed_file_path

        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")
        env["CC_REPO_DIR"] = test_project_macros
        skip_file_path = os.path.join(self.test_dir, 'skipall.txt')

        extract_cmd = ['CodeChecker', 'parse', test_project_macros,
                       '--export', 'gerrit', '--skip', skip_file_path]

        print(" ".join(extract_cmd))
        standard_output, _, result = call_command(
            extract_cmd, cwd=self.test_dir, env=env)
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
        self.assertEqual("[]\n", standard_output,
                         "Result should be an empty json array.")

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
