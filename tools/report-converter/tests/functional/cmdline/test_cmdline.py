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

import json
import os
import subprocess
import tempfile
import unittest


class TestCmdline(unittest.TestCase):
    """ Simple tests to check report-converter command line. """

    def test_help(self):
        """ Get help for report-converter tool. """
        ret = subprocess.call(['report-converter', '--help'])
        self.assertEqual(0, ret)

    def test_metadata(self):
        """ Generate metadata for CodeChecker server. """
        analyzer_version = "x.y.z"
        analyzer_command = "golint simple.go"

        test_dir = os.path.dirname(os.path.realpath(__file__))
        test_file = os.path.join(test_dir, "test_files", "simple.out")
        with tempfile.TemporaryDirectory() as tmp_dir:
            ret = subprocess.call(['report-converter', '-t', 'golint',
                                   '-o', tmp_dir, test_file, '--meta',
                                   'analyzer_version=' + analyzer_version,
                                   'analyzer_command=' + analyzer_command])
            self.assertEqual(0, ret)

            metadata_file = os.path.join(tmp_dir, "metadata.json")
            self.assertTrue(os.path.exists(metadata_file))

            with open(metadata_file, 'r',
                      encoding="utf-8", errors="ignore") as metadata_f:
                metadata = json.load(metadata_f)

                self.assertEqual(metadata['version'], 2)
                self.assertEqual(metadata['num_of_report_dir'], 1)
                self.assertEqual(len(metadata['tools']), 1)

                tool = metadata['tools'][0]
                self.assertEqual(tool['name'], "golint")
                self.assertEqual(tool['version'], analyzer_version)
                self.assertEqual(tool['command'], analyzer_command)
