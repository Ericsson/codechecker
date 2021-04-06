#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test skipping the analysis of a file and the removal
of skipped reports from the report files.
"""


import os
import plistlib
import subprocess
import unittest

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
        self._tu_collector_cmd = env.tu_collector_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')

    def __test_skip(self):
        """Analyze a project with a skip file."""
        test_dir = os.path.join(self.test_dir, "simple")
        build_json = os.path.join(self.test_workspace, "build.json")

        clean_cmd = ["make", "clean"]
        out = subprocess.check_output(clean_cmd,
                                      cwd=test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)

        # Create and run log command.
        log_cmd = [self._codechecker_cmd, "log", "-b", "make",
                   "-o", build_json]
        out = subprocess.check_output(log_cmd,
                                      cwd=test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)
        # Create and run analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", "-c", build_json,
                       "--analyzers", "clangsa", "--verbose", "debug",
                       "--ignore", "skipfile", "-o", self.report_dir]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        print(out)
        print(err)
        errcode = process.returncode
        self.assertEqual(errcode, 0)

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
        report_data = {}
        with open(report_file_to_check, 'rb') as plist_file:
            report_data = plistlib.load(plist_file)
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

    def test_analyze_only_header(self):
        """ Analyze source file which depends on a header file. """
        test_dir = os.path.join(self.test_dir, "multiple")
        build_json = os.path.join(self.test_workspace, "build.json")

        # Create and run log command.
        log_cmd = [self._codechecker_cmd, "log", "-b", "make",
                   "-o", build_json]
        out = subprocess.check_output(log_cmd,
                                      cwd=test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)

        # Use tu_collector to get source file dependencies for a header file
        # and create a skip file from it.
        deps_cmd = [self._tu_collector_cmd, "-l", build_json,
                    "--dependents", "--filter", "*/lib.h"]

        try:
            output = subprocess.check_output(
                deps_cmd,
                cwd=test_dir,
                encoding="utf-8",
                errors="ignore")

            source_files = output.splitlines()
        except subprocess.CalledProcessError as cerr:
            print("Failed to run: " + ' '.join(cerr.cmd))
            print(cerr.output)

        skip_file = os.path.join(self.test_workspace, "skipfile")
        with open(skip_file, 'w', encoding="utf-8", errors="ignore") as skip_f:
            # Include all source file dependencies.
            skip_f.write("\n".join(["+" + s for s in source_files]))

            # Skip all other files.
            skip_f.write("-*")

        analyze_cmd = [self._codechecker_cmd, "analyze", "-c", build_json,
                       "--analyzers", "clangsa",
                       "--ignore", skip_file,
                       "-o", self.report_dir]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        print(out)
        print(err)
        errcode = process.returncode
        self.assertEqual(errcode, 0)

        # Check if file is skipped.
        report_dir_files = os.listdir(self.report_dir)

        # Check that we analyzed all source files which depend on the header
        # file.
        self.assertTrue(any(["a.cpp" in f
                             for f in report_dir_files]))
        self.assertTrue(any(["b.cpp" in f
                             for f in report_dir_files]))
