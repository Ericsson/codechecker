# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Unit tests for bazel_compile_commands tool
"""

import os
import json
import shutil
import unittest

from bazel_compile_commands import bazel_compile_commands


class BazelCompileCommandsTest(unittest.TestCase):
    """ Test class for bazel compile commands generator. """

    TEST_COMPILE_COMMANDS_FILENAME = "test_compile_commands.json"

    @classmethod
    def setUpClass(self):
        """ Initialize test files. """
        self.initial_dir = os.getcwd()
        self.test_proj_dir = os.path.abspath(os.environ["TEST_PROJ"])

    def setUp(self):
        """ Restore initial state. """
        os.chdir(self.test_proj_dir)

    def tearDown(self):
        """ Restore initial state. """
        if os.path.exists(self.TEST_COMPILE_COMMANDS_FILENAME):
            os.remove(self.TEST_COMPILE_COMMANDS_FILENAME)
        os.chdir(self.initial_dir)

    def test_run_command(self):
        """ Test run_command() function. """
        self.assertEqual(bazel_compile_commands.run_command("echo 1"), "1\n")

    def test_empty_run(self):
        """ Test run() function with no arguments. """
        self.assertFalse(bazel_compile_commands.run("", ""))

    @unittest.skipUnless(shutil.which("bazel"), "bazel binary not found!")
    def test_run_bazel(self):
        """ Test run() function with bazel build ... """
        self.assertTrue(bazel_compile_commands.run(
            "bazel build ...", self.TEST_COMPILE_COMMANDS_FILENAME))
        with open(self.TEST_COMPILE_COMMANDS_FILENAME, "r",
                  encoding="utf-8", errors="ignore") as compile_commands_file:
            compile_commands = json.load(compile_commands_file)
            self.assertTrue(compile_commands)
