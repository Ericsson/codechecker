# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Result handler for Clang Tidy.
"""

from typing import Optional

from codechecker_report_converter.analyzers.clang_tidy.analyzer_result import \
    AnalyzerResult
from codechecker_report_converter.analyzers.clang_tidy.parser import Parser
from codechecker_report_converter.report.parser.base import AnalyzerInfo
from codechecker_report_converter.report import report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType

from codechecker_common.logger import get_logger
from codechecker_common.skiplist_handler import SkipListHandlers

from ..result_handler_base import ResultHandler

LOG = get_logger('report')


class ClangTidyResultHandler(ResultHandler):
    """
    Create analyzer result file for Clang Tidy output.
    """

    def __init__(self, *args, **kwargs):
        self.analyzer_info = AnalyzerInfo(name=AnalyzerResult.TOOL_NAME)

        super(ClangTidyResultHandler, self).__init__(*args, **kwargs)

    def postprocess_result(self, skip_handlers: Optional[SkipListHandlers]):
        """
        Generate analyzer result output file which can be parsed and stored
        into the database.
        """
        LOG.debug_analyzer(self.analyzer_stdout)
        tidy_stdout = self.analyzer_stdout.splitlines()

        reports = Parser().get_reports_from_iter(tidy_stdout)
        reports = [r for r in reports if not r.skip(skip_handlers)]

        # In the earlier versions of CodeChecker Clang Tidy never used context
        # free hash even if we enabled it with '--report-hash context-free'
        # when calling the analyze command. To do not break every hash
        # automatically when using this option we introduced a new choice for
        # --report-hash option ('context-free-v2') and we still do not use
        # context free hash for 'context-free' choice.
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
