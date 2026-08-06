#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test parse --export sarif command.
"""

import os
import json
import shutil
import subprocess
import unittest

from libtest import env


class TestParseSarif(unittest.TestCase):
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

        if process.returncode != (2 if "parse" in cmd else 0):
            return err

        return ''.join(out)

    def __log_and_analyze(self, analyze_args=None):
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

        analyze_cmd.extend(analyze_args or [])

        self.__run_cmd(analyze_cmd)

    def test_parse_sarif_rules(self):
        self.__log_and_analyze()

        parse_sarif_cmd = [self._codechecker_cmd, "parse", self.report_dir,
                           "-e", "sarif"]
        out = self.__run_cmd(parse_sarif_cmd)
        parsed_json = json.loads(out)

        rules = parsed_json['runs'][0]['tool']['driver']['rules']
        self.assertEqual(len(rules), 1)

        self.assertEqual(rules[0], {
            'id': 'core.DivideZero',
            'fullDescription': {
                'text': 'Division by zero'
            },
            # pylint: disable-next=line-too-long
            'helpUri': 'https://clang.llvm.org/docs/analyzer/checkers.html#core-dividezero-c-c-objc',  # noqa
            'defaultConfiguration': {
                'level': 'error'
            }
        })

    def test_parse_sarif_suppression_source(self):
        self.__log_and_analyze()

        parse_sarif_cmd = [self._codechecker_cmd, "parse", self.report_dir,
                           "-e", "sarif", "--review-status", "false_positive"]
        out = self.__run_cmd(parse_sarif_cmd)
        parsed_json = json.loads(out)

        res = parsed_json['runs'][0]['results'][0]

        self.assertIn('suppressions', res)
        sups = res['suppressions']
        self.assertEqual(len(sups), 1)
        suppression = sups[0]

        self.assertIn('kind', suppression)
        self.assertIn('status', suppression)
        self.assertIn('justification', suppression)

        self.assertEqual(suppression, {
            'kind': 'inSource',
            'status': 'accepted',
            'justification': 'testing suppression via source code comment',
        })

    def test_parse_sarif_suppression_rs_config(self):
        self.__log_and_analyze([
            "--review-status-config", "review_status.yaml"
        ])

        parse_sarif_cmd = [self._codechecker_cmd, "parse", self.report_dir,
                           "-e", "sarif", "--review-status", "intentional"]
        out = self.__run_cmd(parse_sarif_cmd)
        parsed_json = json.loads(out)

        res = parsed_json['runs'][0]['results'][0]

        self.assertIn('suppressions', res)
        sups = res['suppressions']
        self.assertEqual(len(sups), 1)
        suppression = sups[0]

        self.assertIn('kind', suppression)
        self.assertIn('status', suppression)
        self.assertIn('justification', suppression)

        self.assertEqual(suppression, {
            'kind': 'external',
            'status': 'accepted',
            'justification': 'testing suppression via config file',
        })
