# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from typing import List

from codechecker_report_converter.report import Report

from ..analyzer_result import AnalyzerResultBase
from .parser import Parser


class AnalyzerResult(AnalyzerResultBase):
    """ Transform analyzer result of cpplint. """

    TOOL_NAME = 'cpplint'
    NAME = 'cpplint'
    URL = 'https://github.com/cpplint/cpplint'

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
