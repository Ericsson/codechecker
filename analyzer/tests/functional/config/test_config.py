#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test analyze configuration file.
"""


import json
import os
import subprocess
import unittest

from libtest import env

global TEST_WORKSPACE
# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


class TestConfig(unittest.TestCase):
    _ccClient = None

    def setUp(self):

        TEST_WORKSPACE = env.get_workspace('config')
    
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        self.reports_dir = os.path.join(self.test_workspace, "reports")
        self.config_file_json = os.path.join(
            self.test_workspace, "codechecker.json")
        self.config_file_yaml = os.path.join(
            self.test_workspace, "codechecker.yaml")
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
        simple_file_content = "int main() { return 1/0; }"

        # Write content to the test file
        with open(self.source_file, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(simple_file_content)

    def __run_analyze(self, config_file_path: str, extra_options=None):
        """
        Run the CodeChecker analyze command with a configuration file.
        """
        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", self.build_json,
                       "-o", self.reports_dir,
                       "--config", config_file_path]

        if extra_options:
            analyze_cmd.extend(extra_options)

        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()
        print(err)
        return out, process.returncode

    def __run_parse(self, config_file_path: str):
        """
        Run the CodeChecker analyze command with a configuration file.
        """
        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "parse", self.reports_dir,
                       "--config", config_file_path]

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
        with open(self.config_file_json, 'w+',
                  encoding="utf-8", errors="ignore") as config_f:
            json.dump({
                'analyze': ['--analyzers', 'clangsa']}, config_f)

        out, returncode = self.__run_analyze(self.config_file_json)
        print(out)

        self.assertEqual(returncode, 0)
        self.assertIn("clangsa analyzed simple.cpp", out)
        self.assertNotIn("clang-tidy analyzed simple.cpp", out)

#    def test_config_file_multiple_analyzer_config_resolution(self):
#        """
#        Test whether multiple --analyzer-config arguments from a CodeChecker
#        config file are merged, and don't overwrite one another.
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyzer': [
#                    "--analyzer-config",
#                    "clangsa:track-conditions=false",
#                    "--analyzer-config",
#                    "clang-tidy:HeaderFilterRegex=.*"
#                ]}, config_f)
#
#        out, returncode = self.__run_analyze(self.config_file_json,
#                                             ["--verbose", "debug_analyzer"])
#
#        self.assertNotEqual(returncode, 1)
#        self.assertIn("track-conditions=false", out)
#        self.assertIn("{\"HeaderFilterRegex\": \".*\"}", out)
#
#    def test_config_file_and_cmd_resolution(self):
#        """
#        Test whether multiple --analyzer-config arguments from *both* a
#        CodeChecker config file and the CLI are merged, and don't overwrite one
#        another.
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyzer': [
#                    "--analyzer-config",
#                    "clangsa:track-conditions=false"
#                ]}, config_f)
#
#        out, returncode = self.__run_analyze(self.config_file_json,
#                                             ["--analyzer-config",
#                                              "clang-tidy:"
#                                              "HeaderFilterRegex=.*",
#                                              "--verbose", "debug_analyzer"])
#
#        self.assertNotEqual(returncode, 1)
#        self.assertIn("track-conditions=false", out)
#        self.assertIn("{\"HeaderFilterRegex\": \".*\"}", out)
#
#    def test_cmd_multiple_analyzer_config_resolution(self):
#        """
#        Test whether multiple --analyzer-config arguments from the command line
#        are merged, and don't overwrite one another.
#        """
#
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            config_f.write("")
#
#        out, returncode = self.__run_analyze(self.config_file_json,
#                                             ["--analyzer-config",
#                                              "clang-tidy:"
#                                              "HeaderFilterRegex=.*",
#                                              "--analyzer-config",
#                                              "clangsa:track-conditions=false",
#                                              "--verbose", "debug_analyzer"])
#
#        self.assertNotEqual(returncode, 1)
#        self.assertIn("track-conditions=false", out)
#        self.assertIn("{\"HeaderFilterRegex\": \".*\"}", out)
#
#    def test_cmd_multiple_checker_config_resolution(self):
#        """
#        Test whether multiple --checker-config arguments from the command line
#        are merged, and don't overwrite one another.
#        """
#
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            config_f.write("")
#
#        out, returncode = self.__run_analyze(self.config_file_json,
#                                             ["--checker-config",
#                                              "clangsa:"
#                                              "core.CallAndMessage:"
#                                              "CXXDeallocationArg=true",
#                                              "--checker-config",
#                                              "clangsa:"
#                                              "core.CallAndMessage:"
#                                              "ParameterCount=true",
#                                              "--verbose", "debug_analyzer"])
#
#        self.assertNotEqual(returncode, 1)
#        self.assertIn("core.CallAndMessage:CXXDeallocationArg=true", out)
#        self.assertIn("core.CallAndMessage:ParameterCount=true", out)
#
#    def test_cmd_overrides_config_file(self):
#        """
#        Test the precedence of multiple --analyzer-config arguments specify the
#        same option from both a CodeChecker config file and the CLI, but with a
#        different value. CLI arguments should in effect override the config
#        file (is the later argument in the invocation).
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyze': [
#                    '--analyzers', 'clangsa',
#                    "--analyzer-config",
#                    "clangsa:track-conditions=false"
#                ]}, config_f)
#
#        out, returncode = self.__run_analyze(self.config_file_json,
#                                             ["--analyzer-config",
#                                              "clangsa:track-conditions=true",
#                                              "--verbose", "debug_analyzer"])
#
#        self.assertNotEqual(returncode, 1)
#
#        # If the config from the config file is positioned behind the config
#        # from the CLI, it will override the config file. As intended.
#        cli_idx = out.rfind("track-conditions=true")
#        conf_file_idx = out.rfind("track-conditions=false")
#        self.assertLess(conf_file_idx, cli_idx)
#        self.assertEqual(out.count("track-conditions=true"), 1)
#
#    def test_only_clangsa_config_backward_compatible_mixed(self):
#        """
#        Test the 'analyzer' configuration option backward compatibility.
#        The config name should be 'analyze' to be in sync with the
#        subcommand names.
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyze': ['--analyzers', 'clangsa'],
#                'analyzer': ['--analyzers', 'clang-tidy']},
#                config_f)
#
#        out, returncode = self.__run_analyze(self.config_file_json)
#
#        self.assertEqual(returncode, 0)
#        self.assertIn("clangsa analyzed simple.cpp", out)
#        self.assertNotIn("clang-tidy analyzed simple.cpp", out)
#
#    def test_only_clangsa_config_backward_compatibility(self):
#        """
#        Test the 'analyzer' configuration option backward compatibility.
#        The config name should be 'analyze' to be in sync with the
#        subcommand names.
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyzer': ['--analyzers', 'clangsa']}, config_f)
#
#        out, returncode = self.__run_analyze(self.config_file_json)
#
#        self.assertEqual(returncode, 0)
#        self.assertIn("clangsa analyzed simple.cpp", out)
#        self.assertNotIn("clang-tidy analyzed simple.cpp", out)
#
#    def test_override_config_file(self):
#        """
#        Run analyze command with a config file which enables the clang-tidy
#        analyzer only and override this option from the command line and enable
#        only clangsa analyze.
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyzer': ['--analyzers', 'clang-tidy']}, config_f)
#
#        out, returncode = self.__run_analyze(
#            self.config_file_json, ['--analyzers', 'clangsa'])
#
#        self.assertEqual(returncode, 0)
#        self.assertIn("clangsa analyzed simple.cpp", out)
#        self.assertNotIn("clang-tidy analyzed simple.cpp", out)
#
#    def test_empty_config(self):
#        """
#        Run analyze with an empty config file.
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            config_f.write("")
#
#        out, returncode = self.__run_analyze(self.config_file_json)
#
#        self.assertEqual(returncode, 0)
#        self.assertIn("clangsa analyzed simple.cpp", out)
#        self.assertIn("clang-tidy analyzed simple.cpp", out)
#
#    def test_parse_config(self):
#        """
#        Run analyze command with a JSON config file which enables the clangsa
#        analyzer only and parse the results with a parse command
#        config.
#        """
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyzer': ['--analyzers', 'clangsa'],
#                'parse': ['--trim-path-prefix', '/workspace']},
#                config_f)
#
#        out, returncode = self.__run_analyze(self.config_file_json)
#
#        self.assertEqual(returncode, 0)
#        self.assertIn("clangsa analyzed simple.cpp", out)
#        self.assertNotIn("clang-tidy analyzed simple.cpp", out)
#
#        out, returncode = self.__run_parse(self.config_file_json)
#        print(out)
#        self.assertEqual(returncode, 2)
#
#    def test_yaml_analyze_and_parse(self):
#        """
#        Run analyze command with a yaml config file which enables the clangsa
#        analyzer only and parse the results with a parse command
#        config.
#        """
#        with open(self.config_file_yaml, 'w+',
#                  encoding="utf-8", errors="ignore") as f:
#            f.write("""
#analyzer:
#  # Enable only clangsa analyzer.
#  - --analyzers=clangsa
#
#parse:
#  # Removes leading path from file paths.
#  - --trim-path-prefix=/workspace
#""")
#
#        out, returncode = self.__run_analyze(self.config_file_yaml)
#
#        self.assertEqual(returncode, 0)
#        self.assertIn("clangsa analyzed simple.cpp", out)
#        self.assertNotIn("clang-tidy analyzed simple.cpp", out)
#
#        out, returncode = self.__run_parse(self.config_file_yaml)
#        print(out)
#        self.assertEqual(returncode, 2)
#
#    def test_check_config(self):
#        """
#        Run check command with a config file which enables the clangsa
#        analyzer only and parse the results with a parse command
#        config.
#        """
#        # We assume that the source file path is at least 2 levels deep. This
#        # is true, since the test workspace directory is under the repo root
#        # and it also contains some sub-directories.
#        split_path = self.source_file.split(os.sep)
#        path_prefix = os.path.join(os.sep, *split_path[:3])
#        trimmed_file_path = os.path.join(*split_path[3:])
#
#        with open(self.config_file_json, 'w+',
#                  encoding="utf-8", errors="ignore") as config_f:
#            json.dump({
#                'analyzer': ['--analyzers', 'clangsa'],
#                'parse': ['--trim-path-prefix', path_prefix]},
#                config_f)
#
#        check_cmd = [self._codechecker_cmd, "check",
#                     "-l", self.build_json,
#                     "-o", self.reports_dir,
#                     "--config", self.config_file_json]
#
#        # Run analyze.
#        process = subprocess.Popen(
#            check_cmd,
#            stdout=subprocess.PIPE,
#            stderr=subprocess.PIPE,
#            encoding="utf-8",
#            errors="ignore")
#        out, _ = process.communicate()
#
#        print(out)
#        self.assertEqual(process.returncode, 2)
#        self.assertIn("clangsa analyzed simple.cpp", out)
#        self.assertNotIn("clang-tidy analyzed simple.cpp", out)
#
#        self.assertNotIn(self.source_file, out)
#
#        self.assertIn(trimmed_file_path, out)
