# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Convert between the codechecker_common.Report type and
the thrift ReportData type."""

from typing import Dict
from codechecker_common.report import Report
from codechecker_api.codeCheckerDBAccess_v6.ttypes import ReportData, Severity


def reportData_to_report(report_data: ReportData) -> Report:
    """Create a report object from the given thrift report data."""
    main = {
        "check_name": report_data.checkerId,
        "description": report_data.checkerMsg,
        "issue_hash_content_of_line_in_context": report_data.bugHash,
        "location": {
            "line": report_data.line,
            "col": report_data.column,
            "file": 0,
        },
    }
    bug_path = None
    files = {0: report_data.checkedFile}
    # TODO Can not reconstruct because only the analyzer name was stored
    # it should be a analyzer_name analyzer_version
    return Report(main, bug_path, files, metadata=None)


def report_to_reportData(report: Report,
                         severity_map: Dict[str, str]) -> ReportData:
    """Convert a Report object to a Thrift ReportData type."""
    events = [i for i in report.bug_path if i.get("kind") == "event"]

    report_hash = report.main["issue_hash_content_of_line_in_context"]
    checker_name = report.main["check_name"]

    severity = None
    if severity_map:
        severity_name = severity_map.get(checker_name)
        severity = Severity._NAMES_TO_VALUES[severity_name]

    return ReportData(
        checkerId=checker_name,
        bugHash=report_hash,
        checkedFile=report.file_path,
        checkerMsg=report.main["description"],
        line=report.main["location"]["line"],
        column=report.main["location"]["col"],
        severity=severity,
        bugPathLength=len(events),
    )
