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

from codechecker_common import report
from codechecker_client import report_type_converter
from codechecker_api.codeCheckerDBAccess_v6 import ttypes


class ReportTypeConverterTest(unittest.TestCase):
    """Type conversion tests."""

    def test_Report_to_ReportData(self):
        """Report to reportData conversion."""
        check_name = "checker.name"
        report_hash = "2343we23"
        source_file = "main.cpp"
        description = "some checker message"
        line = 10
        column = 8

        main = {
            "description": description,
            "check_name": check_name,
            "issue_hash_content_of_line_in_context": report_hash,
            "location": {"line": line, "col": column, "file": 0},
        }

        rep = report.Report(main=main,
                            bugpath=[],
                            files={0: source_file},
                            metadata=None)

        severity_map = {check_name: "LOW"}
        rep_data = report_type_converter.report_to_reportData(rep, severity_map)

        self.assertEqual(rep_data.checkerId, rep.check_name)
        self.assertEqual(rep_data.bugHash, rep.report_hash)
        self.assertEqual(rep_data.checkedFile, rep.file_path)
        self.assertEqual(rep_data.line, rep.line)
        self.assertEqual(rep_data.column, rep.col)
        self.assertEqual(rep_data.severity, ttypes.Severity.LOW)

    def test_ReportData_to_Report(self):
        """ReportData to Report conversion."""
        check_name = "checker.name"
        report_hash = "2343we23"
        source_file = "main.cpp"
        description = "some checker message"
        line = 10
        column = 8

        rep_data = ttypes.ReportData(
            checkerId=check_name,
            bugHash=report_hash,
            checkedFile=source_file,
            checkerMsg=description,
            line=line,
            column=column,
            severity="LOW",
            bugPathLength=5,
        )

        rep = report_type_converter.reportData_to_report(rep_data)
        self.assertEqual(rep.check_name, rep_data.checkerId)
        self.assertEqual(rep.report_hash, rep_data.bugHash)
        self.assertEqual(rep.file_path, rep_data.checkedFile)
        self.assertEqual(rep.description, rep_data.checkerMsg)
        self.assertEqual(rep.line, rep_data.line)
        self.assertEqual(rep.col, rep_data.column)
