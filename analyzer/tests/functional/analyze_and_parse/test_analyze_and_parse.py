# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

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
                                                     'CHECK')}

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

        try:
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

                result = subprocess.check_output(
                    shlex.split(command),
                    env=self.env,
                    cwd=self.test_dir,
                    encoding="utf-8",
                    errors="ignore")
                output += result.splitlines(True)

            post_processed_output = []
            skip_prefixes = ["[] - Analysis length:",
                             "[] - Previous analysis results",
                             "[] - Skipping input file"]
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
            return 0
        except CalledProcessError as cerr:
            print("Failed to run: " + ' '.join(cerr.cmd))
            print(cerr.output)
            return cerr.returncode

    def test_json_output_for_macros(self):
        """ Test parse json output for macros. """
        test_project_macros = os.path.join(self.test_workspaces['NORMAL'],
                                           "test_files", "macros")

        extract_cmd = ['CodeChecker', 'parse', "-e", "json",
                       test_project_macros]

        out, _ = call_command(extract_cmd, cwd=self.test_dir, env=self.env)
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

        out, _ = call_command(extract_cmd, cwd=self.test_dir, env=self.env)
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
