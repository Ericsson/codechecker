#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test parse --status command.
"""

import os
import re
import json
import shutil
import subprocess
import unittest

from libtest import env


class TestParseStatus(unittest.TestCase):
    _ccClient = None

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('skip')

        report_dir = os.path.join(TEST_WORKSPACE, 'reports')
        os.makedirs(report_dir)

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    def teardown_class(self):
        """Delete the workspace associated with this test"""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def setup_method(self, _):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._tu_collector_cmd = env.tu_collector_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')

    def __run_cmd(self, cmd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        print(out)
        print(err)

        output = out.splitlines(True)
        processed_output = []
        for line in output:
            # replace timestamps
            line = re.sub(r'\[\w+ \d{4}-\d{2}-\d{2} \d{2}:\d{2}\]',
                          '[]', line)
            processed_output.append(line)

        return ''.join(processed_output)

    def __log_and_analyze(self):
        """ Log and analyze the test project. """
        build_json = os.path.join(self.test_workspace, "build.json")

        clean_cmd = ["make", "clean"]
        out = subprocess.check_output(clean_cmd,
                                      cwd=self.test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)

        # Create and run log command.
        log_cmd = [self._codechecker_cmd, "log", "-b", "make",
                   "-o", build_json]
        out = subprocess.check_output(log_cmd,
                                      cwd=self.test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)

        # Create and run analyze command.
        analyze_cmd = [
            self._codechecker_cmd, "analyze", "-c", build_json,
            "--analyzers", "clangsa", "-o", self.report_dir]

        self.__run_cmd(analyze_cmd)

    def test_parse_status_summary(self):
        self.__log_and_analyze()

        parse_status_cmd = [self._codechecker_cmd, "parse",
                            "--status", self.report_dir]
        out = self.__run_cmd(parse_status_cmd)

        expected_output = """[] - ----==== Summary ====----
[] - Up-to-date analysis results
[] -   clangsa: 2
[] - Outdated analysis results
[] - Failed to analyze
[] - Missing analysis results
[] -   clang-tidy: 2
[] -   cppcheck: 2
[] -   gcc: 2
[] -   infer: 2
[] - Total analyzed compilation commands: 2
[] - Total available compilation commands: 2
[] - ----=================----
"""
        self.assertEqual(out, expected_output)

    def test_parse_status_summary_json(self):
        self.__log_and_analyze()

        parse_status_cmd = [self._codechecker_cmd, "parse",
                            "--status", "-e", "json", self.report_dir]
        out = self.__run_cmd(parse_status_cmd)

        parsed_json = json.loads(out)

        def get_summary_count(analyzer, summary_type):
            return parsed_json["analyzers"][analyzer]["summary"][summary_type]

        self.assertEqual(get_summary_count("clangsa", "up-to-date"), 2)
        self.assertEqual(get_summary_count("clang-tidy", "up-to-date"), 0)
        self.assertEqual(get_summary_count("clang-tidy", "missing"), 2)

    def test_parse_status_detailed_json(self):
        self.__log_and_analyze()

        parse_status_cmd = [self._codechecker_cmd, "parse",
                            "--status", "-e", "json", "--detailed",
                            self.report_dir]
        out = self.__run_cmd(parse_status_cmd)

        parsed_json = json.loads(out)

        def get_file_list(analyzer, list_type):
            return list(map(
                os.path.basename,
                parsed_json["analyzers"][analyzer][list_type]))

        self.assertListEqual(get_file_list("clangsa", "up-to-date"),
                             ["a.cpp", "b.cpp"])
        self.assertListEqual(get_file_list("clang-tidy", "up-to-date"),
                             [])
        self.assertListEqual(get_file_list("clang-tidy", "missing"),
                             ["a.cpp", "b.cpp"])
