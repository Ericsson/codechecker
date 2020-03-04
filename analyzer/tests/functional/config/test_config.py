#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
Test analyze configuration file.
"""


import json
import os
import subprocess
import unittest

from libtest import env


class TestConfig(unittest.TestCase):
    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        self.reports_dir = os.path.join(self.test_workspace, "reports")
        self.config_file = os.path.join(self.test_workspace,
                                        "codechecker.json")
        self.build_json = os.path.join(self.test_workspace,
                                       "build_simple.json")
        self.source_file = os.path.join(self.test_workspace, "simple.cpp")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "g++ -c " + self.source_file,
                      "file": self.source_file
                      }]

        with open(self.build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = "int main() { return 0; }"

        # Write content to the test file
        with open(self.source_file, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(simple_file_content)

    def __run_analyze(self):
        """
        Run the CodeChecker analyze command with a configuration file.
        """
        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", self.build_json,
                       "-o", self.reports_dir,
                       "--config", self.config_file]

        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()
        return out, process.returncode

    def test_only_clangsa_config(self):
        """
        Run analyze command with a config file which enables the clangsa
        analyzer only.
        """
        with open(self.config_file, 'w+',
                  encoding="utf-8", errors="ignore") as config_f:
            json.dump({
                'enabled': True,
                'analyzer': ['--analyzers', 'clangsa']}, config_f)

        out, returncode = self.__run_analyze()

        self.assertEqual(returncode, 0)
        self.assertIn("clangsa analyzed simple.cpp", out)
        self.assertNotIn("clang-tidy analyzed simple.cpp", out)

    def test_empty_config(self):
        """
        Run analyze with an empty config file.
        """
        with open(self.config_file, 'w+',
                  encoding="utf-8", errors="ignore") as config_f:
            config_f.write("")

        out, returncode = self.__run_analyze()

        self.assertEqual(returncode, 0)
        self.assertIn("clangsa analyzed simple.cpp", out)
        self.assertIn("clang-tidy analyzed simple.cpp", out)
