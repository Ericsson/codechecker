# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import glob
import logging
import os

from typing import Dict, List

from codechecker_report_converter.report import BugPathEvent, \
        Range, File, Report, report_file

from ..analyzer_result import AnalyzerResultBase


LOG = logging.getLogger('report-converter')


class AnalyzerResult(AnalyzerResultBase):
    """ Transform analyzer result of Cppcheck. """

    TOOL_NAME = 'cppcheck'
    NAME = 'Cppcheck'
    URL = 'http://cppcheck.sourceforge.net'

    def get_reports(self, analyzer_result_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        reports: List[Report] = []

        plist_files = []
        if os.path.isdir(analyzer_result_path):
            plist_files = glob.glob(os.path.join(
                analyzer_result_path, "*.plist"))
        elif os.path.isfile(analyzer_result_path) and \
                analyzer_result_path.endswith(".plist"):
            plist_files = [analyzer_result_path]
        else:
            LOG.error("The given input should be an existing CppCheck result "
                      "directory or a plist file.")
            return reports

        file_cache: Dict[str, File] = {}
        for plist_file in plist_files:
            plist_reports = report_file.get_reports(
                plist_file, None, file_cache)
            reports.extend(plist_reports)

        # Until we refactor the gui to indicate the error in the location of
        # the diagnostic message, we should add diagnostic message as the
        # last bug path event.
        for report in reports:
            bpe = BugPathEvent(
                    report.message,
                    report.file,
                    report.line,
                    report.column,
                    Range(report.line,
                          report.column,
                          report.line,
                          report.column))
            if bpe != report.bug_path_events[-1]:
                report.bug_path_events.append(bpe)

        return reports
