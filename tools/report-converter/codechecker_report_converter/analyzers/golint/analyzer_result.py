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
    """ Transform analyzer result of Golint. """

    TOOL_NAME = 'golint'
    NAME = 'Golint'
    URL = 'https://github.com/golang/lint'

    EXAMPLE_CMD = """\
# Run Golint and redirect the output to a file.
golint /path/to/your/project > ./golint_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Golint.
report-converter -t golint -o ./codechecker_golint_reports ./golint_reports.out

# Store the Golint reports with CodeChecker.
CodeChecker store ./codechecker_golint_reports -n golint"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
