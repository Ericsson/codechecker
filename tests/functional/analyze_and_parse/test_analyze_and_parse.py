# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""This module tests the CodeChecker 'analyze' and 'parse' feature."""

import glob
import os
import re
import subprocess
import unittest

from subprocess import CalledProcessError

from libtest import env


class AnalyzeParseTestCase(unittest.TestCase):
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

        # Change working dir to testfile dir so CodeChecker can be run easily.
        cls.__old_pwd = os.getcwd()
        os.chdir(cls.test_dir)

    @classmethod
    def teardown_class(cls):
        """Restore environment after tests have ran."""
        os.chdir(cls.__old_pwd)

    def __check_one_file(self, path, mode):
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
        with open(path, 'r') as ofile:
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
        correct_output = ''.join(lines[dash_index + 1:])

        run_name = os.path.basename(path).replace(".output", "")
        workspace = self.test_workspaces[mode]
        os.makedirs(os.path.join(workspace, run_name, "reports"))

        try:
            output = []
            for command in commands:
                split = command.split('#')
                cmode, command = split[0], ''.join(split[1:])

                if cmode != mode:
                    # Ignore the command if its MODE does not match.
                    continue

                command = command.replace("$LOGFILE$",
                                          os.path.join(workspace,
                                                       run_name, "build.json"))
                command = command.replace("$OUTPUT$",
                                          os.path.join(workspace,
                                                       run_name, "reports"))
                result = subprocess.check_output(
                    ['bash', '-c', command], env=self.env, cwd=self.test_dir)
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

    def test_analyze_and_parse_files(self):
        """
        Iterate over the test directory and run all tests in it.
        """
        for ofile in glob.glob(os.path.join(self.test_dir, '*.output')):
            self.assertEqual(self.__check_one_file(ofile, 'NORMAL'), 0)

    def test_check_files(self):
        """
        Iterate over the test directory and run all check (wrapper) tests.
        """
        for ofile in glob.glob(os.path.join(self.test_dir, '*.output')):
            self.assertEqual(self.__check_one_file(ofile, 'CHECK'), 0)
