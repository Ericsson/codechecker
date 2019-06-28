#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
Test skipping the analysis of a file and the removal
of skipped reports from the report files.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import plistlib
import subprocess
import unittest
import shutil

from libtest import env


class TestSkip(unittest.TestCase):
    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        # Change working dir to testfile dir so CodeChecker can be run easily.
        self.__old_pwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Restore environment after tests have ran."""
        os.chdir(self.__old_pwd)
        if os.path.isdir(self.report_dir):
            shutil.rmtree(self.report_dir)

    def test_skip(self):
        """
        """
        build_json = os.path.join(self.test_workspace, "build.json")

        clean_cmd = ["make", "clean"]
        out = subprocess.check_output(clean_cmd)
        print(out)

        # Create and run log command.
        log_cmd = [self._codechecker_cmd, "log", "-b", "make",
                   "-o", build_json]
        out = subprocess.check_output(log_cmd)
        print(out)
        # Create and run analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "--verbose", "debug",
                       "--ignore", "skipfile", "-o", self.report_dir]

        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.test_dir)
        out, err = process.communicate()

        print(out)
        print(err)
        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # Check if file is skipped.
        report_dir_files = os.listdir(self.report_dir)
        for f in report_dir_files:
            self.assertFalse("file_to_be_skipped.cpp" in f)

        # Check if report from the report file is removed.
        report_dir_files = os.listdir(self.report_dir)
        report_file_to_check = None
        for f in report_dir_files:
            if "skip_header.cpp" in f:
                report_file_to_check = os.path.join(self.report_dir, f)
                break

        self.assertIsNotNone(report_file_to_check,
                             "Report file should be generated.")
        report_data = plistlib.readPlist(report_file_to_check)
        files = report_data['files']

        skiped_file_index = None
        for i, f in enumerate(files):
            if "skip.h" in f:
                skiped_file_index = i
                break

        for diag in report_data['diagnostics']:
            self.assertNotEqual(diag['location']['file'],
                                skiped_file_index,
                                "Found a location which points to "
                                "skiped file, this report should "
                                "have been removed.")
