#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" analyze function test.

WARNING!!!
This is a generated test skeleton remove the parts not required by the tests.
WARNING!!!

"""
import os
import unittest
import subprocess
import json

from libtest import env


class TestSkeleton(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        os.makedirs(self.report_dir)
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        # Change working dir to testfile dir so CodeChecker can be run easily.
        os.chdir(self.test_dir)

    def test_failure(self):
        """
        Test if reports/failed/<failed_file>.error
        file is created in case of compilation & analysis error
        """
        build_json = os.path.join(self.test_workspace, "build.json")
        reports_dir = os.path.join(self.test_workspace, "reports")
        failed_dir = os.path.join(reports_dir, "failed")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", reports_dir]

        source_file = os.path.join(self.test_dir, "failure.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c "+source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
                    analyze_cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, cwd=self.test_dir)
        out, err = process.communicate()
        print(out+err)
        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # We expect a failure file to be in the failed directory
        failed_files = os.listdir(failed_dir)
        print(failed_files)
        self.assertEquals(len(failed_files), 1)
