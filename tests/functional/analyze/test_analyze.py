#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" analyze function test."""

import os
import unittest
import subprocess
import json

from libtest import env


class TestAnalyze(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._test_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        # Change working dir to testfile dir so CodeChecker can be run easily.
        os.chdir(self._test_dir)

    def __get_plist_files(self, reportdir):
        return [os.path.join(reportdir, filename)
                for filename in os.listdir(reportdir)
                if filename.endswith('.plist')]

    def __analyze_incremental(self, content_, build_json, reports_dir,
                              plist_count, failed_count):
        """
        Helper function to test analyze incremental mode. It's create a file
        with the given content. Run analyze on that file and checks the count
        of the plist end error files.
        """
        source_file = os.path.join(self.test_workspace, "simple.cpp")

        # Write content to the test file
        with open(source_file, 'w') as source:
            source.write(content_)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", reports_dir]

        # Run analyze
        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self._test_dir)
        process.communicate()

        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # Check the count of the plist files.
        plist_files = [os.path.join(reports_dir, filename)
                       for filename in os.listdir(reports_dir)
                       if filename.endswith('.plist')]
        self.assertEquals(len(plist_files), plist_count)

        # Check the count of the error files.
        failed_dir = os.path.join(reports_dir, "failed")
        failed_file_count = 0
        if os.path.exists(failed_dir):
            failed_files = [os.path.join(failed_dir, filename)
                            for filename in os.listdir(failed_dir)
                            if filename.endswith('.error')]
            failed_file_count = len(failed_files)
        self.assertEquals(failed_file_count, failed_count)

    def test_failure(self):
        """
        Test if reports/failed/<failed_file>.error
        file is created in case of compilation & analysis error
        """
        build_json = os.path.join(self.test_workspace, "build_fail.json")
        reports_dir = os.path.join(self.test_workspace, "reports_fail")
        failed_dir = os.path.join(reports_dir, "failed")
        source_file = os.path.join(self._test_dir, "failure.c")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c "+source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        # Create and run analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", reports_dir]

        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self._test_dir)
        process.communicate()

        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # We expect a failure file to be in the failed directory
        failed_files = os.listdir(failed_dir)
        self.assertEquals(len(failed_files), 1)

    def test_incremental_analyze(self):
        """
        Test incremental mode to analysis command which overwrites only those
        plist files that were update by the current build command.
        """
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        reports_dir = os.path.join(self.test_workspace, "reports_incremental")
        source_file = os.path.join(self.test_workspace, "simple.cpp")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c "+source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = "int main() { return 0; }"
        failed_file_content = "int main() { err; return 0; }"

        # Run analyze on the simple file.
        self.__analyze_incremental(simple_file_content, build_json,
                                   reports_dir, 1, 0)

        # Run analyze on the failed file.
        self.__analyze_incremental(failed_file_content, build_json,
                                   reports_dir, 0, 1)

        # Run analyze on the simple file again.
        self.__analyze_incremental(simple_file_content, build_json,
                                   reports_dir, 1, 0)
