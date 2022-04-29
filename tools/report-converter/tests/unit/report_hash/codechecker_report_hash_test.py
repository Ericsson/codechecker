# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for the CodeChecker report hash. """

import os
import unittest
import shutil
import plistlib
import tempfile

from codechecker_report_converter.report.hash import get_report_hash, \
    get_report_path_hash, HashType
from codechecker_report_converter.report.report_file import get_reports, \
    replace_report_hash


class CodeCheckerReportHashTest(unittest.TestCase):
    """ Testing CodeChecker report hash generation. """

    @classmethod
    def setUpClass(self):
        """ Initialize test files. """
        self.test_proj_dir = os.path.abspath(os.environ['TEST_PROJ'])
        self.test_workspace = os.environ['TEST_WORKSPACE']
        self.test_file_dir = os.path.join(self.test_workspace, "test_files")

        for test_project in os.listdir(self.test_proj_dir):
            test_project_path = os.path.join(self.test_file_dir, test_project)
            shutil.copytree(os.path.join(self.test_proj_dir, test_project),
                            test_project_path)

            for test_file in os.listdir(test_project_path):
                if test_file.endswith(".plist"):
                    test_file_path = os.path.join(test_project_path, test_file)
                    with open(test_file_path, 'r+') as plist_file:
                        content = plist_file.read()
                        new_content = content.replace("$FILE_PATH$",
                                                      test_project_path)
                        plist_file.seek(0)
                        plist_file.truncate()
                        plist_file.write(new_content)

    def test_gen_report_hash_path_sensitive(self):
        """ Test path sensitive report hash generation for multiple errors. """
        test_plist = os.path.join(
            self.test_file_dir, 'cpp', 'multi_error.plist')

        expected_report_hash = {
            'f48840093ef89e291fb68a95a5181612':
                'fdf11db1183dba2da4cd188e70d142e5',
            'e4907182b363faf2ec905fc32cc5a4ab':
                '774799eb31f5fb8514988a7f6736b33e'}

        reports = get_reports(test_plist)
        for report in reports:
            report_hash = get_report_hash(report, HashType.PATH_SENSITIVE)
            self.assertEqual(report_hash,
                             expected_report_hash[report.report_hash])

    def test_gen_report_hash_context_free(self):
        """ Test context free hash generation for multi errors. """
        test_plist = os.path.join(
            self.test_file_dir, 'cpp', 'multi_error.plist')

        expected_report_hash = {
            'f48840093ef89e291fb68a95a5181612':
                'c2a2856f566ed67ed1c3596ad06d42db',
            'e4907182b363faf2ec905fc32cc5a4ab':
                '5a92e13f07c81c6d3197e7d910827e6e'}

        reports = get_reports(test_plist)
        for report in reports:
            report_hash = get_report_hash(report, HashType.CONTEXT_FREE)
            self.assertEqual(report_hash,
                             expected_report_hash[report.report_hash])

    def test_gen_report_path_hash(self):
        """ Test path hash generation for multiple errors. """
        test_plist = os.path.join(
            self.test_file_dir, 'cpp', 'multi_error.plist')

        expected_path_hash = {
            'f48840093ef89e291fb68a95a5181612':
                'b053ba21d4d1f0ad2ef0d5a244c19ea4',
            'e4907182b363faf2ec905fc32cc5a4ab':
                'de139052a89686cc13828ae9e1e1cc5f'}

        reports = get_reports(test_plist)
        for report in reports:
            report_hash = get_report_path_hash(report)
            self.assertEqual(report_hash,
                             expected_path_hash[report.report_hash])

    def test_replace_report_hash_in_empty_plist(self):
        """ Test replacing hash in an empty plist file. """
        with tempfile.NamedTemporaryFile("wb+",
                                         suffix='.plist') as empty_plist_file:
            content = {'diagnostics': [], 'files': []}
            plistlib.dump(content, empty_plist_file)
            empty_plist_file.flush()
            empty_plist_file.seek(0)

            replace_report_hash(empty_plist_file.name, HashType.CONTEXT_FREE)
            empty_plist_file.flush()
            empty_plist_file.seek(0)

            # Check that plist file is not empty.
            self.assertNotEqual(empty_plist_file.read(), b'')

    def test_gen_report_hash_diag_messages(self):
        """ Test diagnostic message hash generation for multi errors. """
        test_plist = os.path.join(
            self.test_file_dir, 'cpp', 'multi_error.plist')

        expected_report_hash = {
            'f48840093ef89e291fb68a95a5181612':
                'c137804816bf2d5a67b6c067cd2ab5e8',
            'e4907182b363faf2ec905fc32cc5a4ab':
                'd08c2f8c5c4d8533e1de3fa88241f813'}

        reports = get_reports(test_plist)
        for report in reports:
            report_hash = get_report_hash(report, HashType.DIAGNOSTIC_MESSAGE)
            self.assertEqual(report_hash,
                             expected_report_hash[report.report_hash])
