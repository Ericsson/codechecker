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

    EXAMPLE_CMD = """\
# Run cpplint and redirect the output to a file.
cpplint sample.cpp > ./sample.out 2>&1

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of cpplint.
report-converter -t cpplint -o ./codechecker_cpplint_reports ./sample.out

# Store the cpplint reports with CodeChecker.
CodeChecker store ./codechecker_cpplint_reports -n cpplint"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
