# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Convert between Report type and thrift ReportData type. """

from typing import Callable
from codechecker_api.codeCheckerDBAccess_v6.ttypes import ReportData, Severity

from codechecker_report_converter.report import File, Report


def to_report(
    report: ReportData,
    get_file: Callable[[int, str], File]
) -> Report:
    """ Create a Report object from the given thrift report data. """
    severity = Severity._VALUES_TO_NAMES[report.severity] \
        if report.severity else 'UNSPECIFIED'

    return Report(
        get_file(report.fileId, report.checkedFile),
        report.line,
        report.column,
        report.checkerMsg,
        report.checkerId,
        severity,
        report.bugHash,
        report.analyzerName)


def to_report_data(
    report: Report
) -> ReportData:
    """ Convert a Report object to a Thrift ReportData type. """
    severity = Severity._NAMES_TO_VALUES[report.severity or 'UNSPECIFIED']
    return ReportData(
        checkerId=report.checker_name,
        bugHash=report.report_hash,
        checkedFile=report.file.path,
        checkerMsg=report.message,
        line=report.line,
        column=report.column,
        severity=severity,
        analyzerName=report.analyzer_name,
        bugPathLength=len(report.bug_path_events))
