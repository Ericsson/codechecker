# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Result handler for Cppcheck.
"""
from typing import Optional

from codechecker_report_converter.report.parser.base import AnalyzerInfo
from codechecker_report_converter.analyzers.cppcheck.analyzer_result import \
    AnalyzerResult
from codechecker_report_converter.report import report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType

from codechecker_common.logger import get_logger
from codechecker_common.skiplist_handler import SkipListHandlers

from ..result_handler_base import ResultHandler

LOG = get_logger('analyzer.cppcheck')


class CppcheckResultHandler(ResultHandler):
    """
    Use context free hash if enabled.
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

        reports = AnalyzerResult().get_reports(self.workspace)
        reports = [r for r in reports if not r.skip(skip_handlers)]

        hash_type = HashType.PATH_SENSITIVE
        if self.report_hash_type == 'context-free-v2':
            hash_type = HashType.CONTEXT_FREE
        elif self.report_hash_type == 'diagnostic-message':
            hash_type = HashType.DIAGNOSTIC_MESSAGE

        for report in reports:
            report.report_hash = get_report_hash(report, hash_type)

        report_file.create(
            self.analyzer_result_file, reports, self.checker_labels,
            self.analyzer_info)
