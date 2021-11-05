# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import json
import logging
import os

from typing import Dict, List, Optional

from codechecker_report_converter.report import BugPathEvent, File, \
    get_or_create_file, Report

from ..analyzer_result import AnalyzerResultBase


LOG = logging.getLogger('report-converter')


class AnalyzerResult(AnalyzerResultBase):
    """ Transform analyzer result of the FB Infer. """

    TOOL_NAME = 'fbinfer'
    NAME = 'Facebook Infer'
    URL = 'https://fbinfer.com'

    def __init__(self):
        super(AnalyzerResult, self).__init__()
        self.__infer_out_parent_dir = None
        self.__file_cache: Dict[str, File] = {}

    def get_reports(self, result_file_path: str) -> List[Report]:
        """ Parse the given analyzer result. """
        reports: List[Report] = []

        if os.path.isdir(result_file_path):
            report_file = os.path.join(result_file_path, "report.json")
            self.__infer_out_parent_dir = os.path.dirname(result_file_path)
        else:
            report_file = result_file_path
            self.__infer_out_parent_dir = os.path.dirname(
                os.path.dirname(result_file_path))

        if not os.path.exists(report_file):
            LOG.error("Report file does not exist: %s", report_file)
            return reports

        try:
            with open(report_file, 'r',
                      encoding="utf-8", errors="ignore") as f:
                bugs = json.load(f)
        except IOError:
            LOG.error("Failed to parse the given analyzer result '%s'. Please "
                      "give a infer output directory which contains a valid "
                      "'report.json' file.", result_file_path)
            return reports

        for bug in bugs:
            report = self.__parse_report(bug)
            if report:
                reports.append(report)

        return reports

    def __get_abs_path(self, source_path):
        """ Returns full path of the given source path.
        It will try to find the given source path relative to the given
        analyzer report directory (infer-out).
        """
        if os.path.exists(source_path):
            return os.path.abspath(source_path)

        full_path = os.path.join(self.__infer_out_parent_dir, source_path)
        if os.path.exists(full_path):
            return full_path

        LOG.warning("No source file found: %s", source_path)

    def __parse_report(self, bug) -> Optional[Report]:
        """ Parse the given report and create a message from them. """
        report_hash = bug['hash']
        checker_name = bug['bug_type']

        message = bug['qualifier']
        line = int(bug['line'])
        col = int(bug['column'])
        if col < 0:
            col = 0

        source_path = self.__get_abs_path(bug['file'])
        if not source_path:
            return None

        report = Report(
            get_or_create_file(
                os.path.abspath(source_path), self.__file_cache),
            line, col, message, checker_name,
            report_hash=report_hash,
            bug_path_events=[])

        for bug_trace in bug['bug_trace']:
            event = self.__parse_bug_trace(bug_trace)

            if event:
                report.bug_path_events.append(event)

        report.bug_path_events.append(BugPathEvent(
            report.message, report.file, report.line, report.column))

        return report

    def __parse_bug_trace(self, bug_trace) -> Optional[BugPathEvent]:
        """ Creates event from a bug trace element. """
        source_path = self.__get_abs_path(bug_trace['filename'])
        if not source_path:
            return None

        message = bug_trace['description']
        line = int(bug_trace['line_number'])
        col = int(bug_trace['column_number'])
        if col < 0:
            col = 0

        return BugPathEvent(
            message,
            get_or_create_file(source_path, self.__file_cache),
            line,
            col)
