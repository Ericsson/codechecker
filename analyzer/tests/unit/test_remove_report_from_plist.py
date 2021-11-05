# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for removing report from plist by using skip file. """

import os
import unittest

from codechecker_report_converter.report import report_file, \
    reports as reports_handler

from codechecker_common.skiplist_handler import SkipListHandler


OLD_PWD = None


def setup_module():
    """ Change to the directory with sample version outputs. """
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
             'remove_report_test_files'))


def teardown_module():
    """ Restore the current working directory. """
    global OLD_PWD
    os.chdir(OLD_PWD)


class TestRemoveReportFromPlist(unittest.TestCase):
    """ Test skipping header files. """

    def __test_skip_reports(
        self,
        plist_file_path: str,
        expected_plist_file_path: str,
        skip_handler: SkipListHandler
    ):
        """ Test skipping reports from a plist file. """
        reports = report_file.get_reports(plist_file_path)
        reports = reports_handler.skip(reports, skip_handler=skip_handler)

        expected_reports = report_file.get_reports(expected_plist_file_path)

        self.assertEqual(reports, expected_reports)

    def test_skip_x_header(self):
        """ Test skipping a header file. """
        with open('skip_x_header.txt',
                  encoding="utf-8", errors="ignore") as skip_file:
            skip_handler = SkipListHandler(skip_file.read())

        self.__test_skip_reports(
            'x.plist', 'skip_x_header.expected.plist', skip_handler)

    def test_skip_all_header(self):
        """ Test skipping all header files. """
        with open('skip_all_header.txt',
                  encoding="utf-8", errors="ignore") as skip_file:
            skip_handler = SkipListHandler(skip_file.read())

        self.__test_skip_reports(
            'x.plist', 'skip_all_header.expected.plist', skip_handler)

    def test_keep_only_empty(self):
        """ Test skipping all files except empty. """
        with open('keep_only_empty.txt',
                  encoding="utf-8", errors="ignore") as skip_file:
            skip_handler = SkipListHandler(skip_file.read())

        self.__test_skip_reports(
            'x.plist', 'keep_only_empty.expected.plist', skip_handler)
