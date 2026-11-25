# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the report-converter tool.
"""

import glob
import os
import subprocess
import tempfile
import unittest


class TestCmdline(unittest.TestCase):
    """ Simple tests to check report-converter command line. """

    def test_help(self):
        """ Get help for report-converter tool. """
        ret = subprocess.call(['report-converter', '--help'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        self.assertEqual(0, ret)

    def test_nonexistent_file(self):
        """ Get help for report-converter tool. """
        process = subprocess.Popen(['report-converter', '-t', 'gcc',
                                    '-o', 'reports/', 'non_existent.sarif'],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   encoding="utf-8",
                                   universal_newlines=True)
        out, _ = process.communicate()
        self.assertIn("'non_existent.sarif' does not exist", out)
        self.assertEqual(1, process.returncode)

    def test_input_dir(self):
        """ Execution with file and directory inputs. """
        def count_reports(report_dir):
            counter = 0

            for plist_file in os.listdir(report_dir):
                plist_file = os.path.join(report_dir, plist_file)
                with open(plist_file, encoding="utf-8", errors="ignore") as f:
                    counter += f.read().count(
                        "issue_hash_content_of_line_in_context")

            return counter

        test_dir = os.path.dirname(os.path.realpath(__file__))
        outputs_dir = os.path.join(test_dir, "test_files", "test_outputs")

        with tempfile.TemporaryDirectory() as tmp_dir:
            ret = subprocess.call(['report-converter', '-t', 'golint',
                                   '-o', tmp_dir, outputs_dir])
            self.assertEqual(0, ret)

            self.assertEqual(
                len(glob.glob(os.path.join(tmp_dir, '*.plist'))), 3)

            self.assertEqual(count_reports(tmp_dir), 4)

        test_input1 = os.path.join(outputs_dir, "subdir", "simple2.out")
        test_input2 = os.path.join(outputs_dir, "subdir", "simple3.out")
        with tempfile.TemporaryDirectory() as tmp_dir:
            ret = subprocess.call(['report-converter', '-t', 'golint',
                                   '-o', tmp_dir, test_input1, test_input2])
            self.assertEqual(0, ret)

            self.assertEqual(
                len(glob.glob(os.path.join(tmp_dir, '*.plist'))), 2)

            self.assertEqual(count_reports(tmp_dir), 3)
