# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the memory_safety_reporter tool.
"""

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile


class TestCmdline(unittest.TestCase):
    """ Simple tests to check memory_safety_reporter command line. """

    def test_help(self):
        """ Get help for memory_safety_reporter tool. """
        ret = subprocess.run(
            [sys.executable, "memory_safety_reporter.py", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        self.assertEqual(0, ret.returncode)

    def test_nonexistent_report_dir(self):
        """ Test memory_safety_reporter if the report dir does not exist. """
        ret = subprocess.run(
            [sys.executable, "memory_safety_reporter.py", "-r", "notexists"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        self.assertIn(
            "Report directory 'notexists' does not exist!",
            ret.stdout
        )
        self.assertEqual(1, ret.returncode)

    def test_basic_run(self):
        """ Test memory_safety_reporter with only the required args """
        test_dir = os.path.dirname(os.path.realpath(__file__))
        test_report_dir = os.path.join(test_dir, "test-report")
        with tempfile.TemporaryDirectory() as tmp_dir:
            ret = subprocess.run(
                [
                    sys.executable,
                    os.path.join(test_dir, "memory_safety_reporter.py"),
                    "-r", test_report_dir
                ],
                cwd=tmp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            output_file = os.path.join(tmp_dir, "memory_safety_report.zip")
            print(os.listdir(tmp_dir))
            self.assertTrue(os.path.exists(output_file))

            expected_files = [
                "memory_safety_report/CHECKSUMS.sha256",
                "memory_safety_report/checker_details.json",
                "memory_safety_report/metadata.json",
                "memory_safety_report/reports.sarif",
                "memory_safety_report/config/"
            ]

            with zipfile.ZipFile(output_file, "r") as zf:
                contents = zf.namelist()
                for file in expected_files:
                    self.assertIn(file, contents)

            self.assertEqual(0, ret.returncode)

    def test_all_arguments_run(self):
        """ Test memory_safety_reporter with all arguments """
        test_dir = os.path.dirname(os.path.realpath(__file__))
        test_report_dir = os.path.join(test_dir, "test-report")
        output_file = 'MemorySafetyReportTest'
        product_name = 'prod'
        revision = 'rev'
        binary = 'bin'
        build_id = '1234'
        timestamp = '20260729154400'
        with tempfile.TemporaryDirectory() as tmp_dir:
            ret = subprocess.run(
                [
                    sys.executable,
                    os.path.join(test_dir, "memory_safety_reporter.py"),
                    '-o', output_file,
                    '-r', test_report_dir,
                    '-p', product_name,
                    '-v', revision,
                    '-b', binary,
                    '-d', build_id,
                    '-t', timestamp,
                    '-x', 'gztar'
                ],
                cwd=tmp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            filename = (f"{output_file}_{product_name}_{revision}_{binary}_" +
                        f"{build_id}_{timestamp}.tar.gz")
            print(os.listdir(tmp_dir))
            output_file_path = os.path.join(
                tmp_dir,
                filename
            )
            print(output_file_path)
            self.assertTrue(os.path.exists(output_file_path))
            self.assertEqual(0, ret.returncode)
