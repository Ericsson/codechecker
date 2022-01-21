# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Convert between Report type and thrift ReportData type. """

from typing import Callable, List

from codechecker_api.codeCheckerDBAccess_v6.ttypes import \
    ExtendedReportDataType, ReportData, Severity

from codechecker_report_converter.report import BugPathEvent, \
    BugPathPosition, File, MacroExpansion, Range, Report


def to_report(
    report: ReportData,
    get_file: Callable[[int, str], File]
) -> Report:
    """ Create a Report object from the given thrift report data. """
    severity = Severity._VALUES_TO_NAMES[report.severity] \
        if report.severity else 'UNSPECIFIED'

    bug_path_events: List[BugPathEvent] = []
    bug_path_positions: List[BugPathPosition] = []
    notes: List[BugPathEvent] = []
    macro_expansions: List[MacroExpansion] = []

    details = report.details
    if details:
        for e in details.pathEvents:
            bug_path_events.append(BugPathEvent(
                e.msg,
                get_file(e.fileId, e.filePath),
                e.startLine,
                e.startCol,
                Range(e.startLine, e.startCol, e.endLine, e.endCol)))

        for p in details.executionPath:
            bug_path_positions.append(BugPathPosition(
                get_file(p.fileId, p.filePath),
                Range(p.startLine, p.startCol, p.endLine, p.endCol)))

        for e in details.extendedData:
            if e.type == ExtendedReportDataType.NOTE:
                notes.append(BugPathEvent(
                    e.message,
                    get_file(e.fileId, e.filePath),
                    e.startLine,
                    e.startCol,
                    Range(e.startLine, e.startCol, e.endLine, e.endCol)))

            if e.type == ExtendedReportDataType.MACRO:
                name = ''
                macro_expansions.append(MacroExpansion(
                    e.message,
                    name,
                    get_file(e.fileId, e.filePath),
                    e.startLine,
                    e.startCol,
                    Range(e.startLine, e.startCol, e.endLine, e.endCol)))

    return Report(
        get_file(report.fileId, report.checkedFile),
        report.line,
        report.column,
        report.checkerMsg,
        report.checkerId,
        severity,
        report.bugHash,
        report.analyzerName,
        bug_path_events=bug_path_events or None,
        bug_path_positions=bug_path_positions,
        notes=notes,
        macro_expansions=macro_expansions)


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
