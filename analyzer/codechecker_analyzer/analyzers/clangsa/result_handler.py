# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Result handler for Clang Static Analyzer.
"""

import os

from typing import Optional

from codechecker_report_converter.report.parser.base import AnalyzerInfo
from codechecker_report_converter.report import report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType
from codechecker_common.logger import get_logger
from codechecker_common.skiplist_handler import SkipListHandlers

from ..result_handler_base import ResultHandler

LOG = get_logger('report')


class ClangSAResultHandler(ResultHandler):
    """
    Create analyzer result file for Clang Static Analyzer output.
    """

    def __init__(self, *args, **kwargs):
        self.analyzer_info = AnalyzerInfo(name='clangsa')

        super(ClangSAResultHandler, self).__init__(*args, **kwargs)

    def postprocess_result(self, skip_handlers: Optional[SkipListHandlers]):
        """
        Generate analyzer result output file which can be parsed and stored
        into the database.
        """
        if os.path.exists(self.analyzer_result_file):
            reports = report_file.get_reports(
                self.analyzer_result_file, self.checker_labels,
                source_dir_path=self.source_dir_path)
            reports = [r for r in reports if not r.skip(skip_handlers)]

            hash_type = None
            if self.report_hash_type in ['context-free', 'context-free-v2']:
                hash_type = HashType.CONTEXT_FREE
            elif self.report_hash_type == 'diagnostic-message':
                hash_type = HashType.DIAGNOSTIC_MESSAGE

            if hash_type is not None:
                for report in reports:
                    report.report_hash = get_report_hash(report, hash_type)

            report_file.create(
                self.analyzer_result_file, reports, self.checker_labels,
                self.analyzer_info)
