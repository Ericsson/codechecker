# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from typing import List

from codechecker_report_converter.report import Report
from codechecker_report_converter.report.hash import get_report_hash, HashType

from ..analyzer_result import AnalyzerResultBase
from .parser import Parser


class AnalyzerResult(AnalyzerResultBase):
    """ Transform analyzer result of Clang Tidy. """

    TOOL_NAME = 'clang-tidy-yaml'
    NAME = 'Clang Tidy'
    URL = 'https://clang.llvm.org/extra/clang-tidy'

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser().get_reports(file_path)

    def _add_report_hash(self, report: Report):
        # Due to backward compatibility, the CodeChecker analyzer
        # uses hash type PATH_SENSITIVE for ClangTidy by default.
        report.report_hash = get_report_hash(report, HashType.PATH_SENSITIVE)
