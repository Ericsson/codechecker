# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test the report converter between the common Report type and the
thrift ReportData type
"""

import unittest

from codechecker_report_converter.report import File, Report

from codechecker_client import report_type_converter
from codechecker_api.codeCheckerDBAccess_v6 import ttypes


class ReportTypeConverterTest(unittest.TestCase):
    """Type conversion tests."""

    def test_Report_to_ReportData(self):
        """ Report to reportData conversion. """
        checker_name = "checker.name"
        report = Report(
            file=File("main.cpp"),
            line=10,
            column=8,
            message="some checker message",
            checker_name=checker_name,
            report_hash="2343we23",
            analyzer_name="dummy.analyzer",
            severity="LOW"
        )

        rep_data = report_type_converter.to_report_data(report)

        self.assertEqual(rep_data.checkerId, report.checker_name)
        self.assertEqual(rep_data.bugHash, report.report_hash)
        self.assertEqual(rep_data.checkedFile, report.file.path)
        self.assertEqual(rep_data.line, report.line)
        self.assertEqual(rep_data.column, report.column)
        self.assertEqual(rep_data.analyzerName, report.analyzer_name)
        self.assertEqual(rep_data.severity, ttypes.Severity.LOW)

    def test_ReportData_to_Report(self):
        """ ReportData to Report conversion. """
        rep_data = ttypes.ReportData(
            checkerId="checker.name",
            bugHash="2343we23",
            checkedFile="main.cpp",
            checkerMsg="some checker message",
            line=10,
            column=8,
            severity=ttypes.Severity.LOW,
            analyzerName="dummy.analyzer",
            bugPathLength=5,
        )

        report = report_type_converter.to_report(rep_data)
        self.assertEqual(report.checker_name, rep_data.checkerId)
        self.assertEqual(report.report_hash, rep_data.bugHash)
        self.assertEqual(report.file.path, rep_data.checkedFile)
        self.assertEqual(report.message, rep_data.checkerMsg)
        self.assertEqual(report.line, rep_data.line)
        self.assertEqual(report.column, rep_data.column)
        self.assertEqual(report.analyzer_name, rep_data.analyzerName)
