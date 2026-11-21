# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test cases for dump_changed_files. """

import unittest
from unittest.mock import patch

from codechecker_report_converter.report import reports


class DumpChangedFilesTestCase(unittest.TestCase):
    """ Test cases for dump_changed_files. """

    @patch('codechecker_report_converter.report.reports.LOG')
    def test_dump_changed_files_emits_error(self, mock_log):
        """ Test that error is logged when files have changed. """
        reports.dump_changed_files({'/tmp/test.cpp'})

        mock_log.error.assert_called_once()
        mock_log.warning.assert_not_called()

    @patch('codechecker_report_converter.report.reports.LOG')
    def test_dump_changed_files_empty_set_no_log(self, mock_log):
        """ Test that nothing is logged when changed files set is empty. """
        reports.dump_changed_files(set())

        mock_log.error.assert_not_called()
        mock_log.warning.assert_not_called()
