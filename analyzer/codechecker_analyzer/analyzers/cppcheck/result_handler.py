# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Result handler for Cppcheck.
"""
from typing import Optional

from codechecker_report_converter.report.parser.base import AnalyzerInfo
from codechecker_report_converter.analyzers.cppcheck.analyzer_result import \
    AnalyzerResult
from codechecker_report_converter.report import BugPathEvent, \
        Range, report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType

from codechecker_common.logger import get_logger
from codechecker_common.skiplist_handler import SkipListHandlers

from ..result_handler_base import ResultHandler

LOG = get_logger('analyzer.cppcheck')


class CppcheckResultHandler(ResultHandler):
    """
    Create analyzer result file for Cppcheck output.
    """

    def __init__(self, *args, **kwargs):
        self.analyzer_info = AnalyzerInfo(name=AnalyzerResult.TOOL_NAME)

        super(CppcheckResultHandler, self).__init__(*args, **kwargs)

    def postprocess_result(self, skip_handlers: Optional[SkipListHandlers]):
        """
        Generate analyzer result output file which can be parsed and stored
        into the database.
        """
        LOG.debug_analyzer(self.analyzer_stdout)

        reports = report_file.get_reports(
            self.analyzer_result_file, self.checker_labels,
            source_dir_path=self.source_dir_path)

        reports = [r for r in reports if not r.skip(skip_handlers)]
        for report in reports:
            # TODO check if prefix cascading still occurs.
            if not report.checker_name.startswith("cppcheck-"):
                report.checker_name = "cppcheck-" + report.checker_name

        hash_type = HashType.PATH_SENSITIVE
        if self.report_hash_type == 'context-free-v2':
            hash_type = HashType.CONTEXT_FREE
        elif self.report_hash_type == 'diagnostic-message':
            hash_type = HashType.DIAGNOSTIC_MESSAGE

        for report in reports:
            report.report_hash = get_report_hash(report, hash_type)
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

        report_file.create(
            self.analyzer_result_file, reports, self.checker_labels,
            self.analyzer_info)
