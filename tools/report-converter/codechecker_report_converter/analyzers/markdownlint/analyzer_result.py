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
    """ Transform analyzer result of Markdownlint. """

    TOOL_NAME = 'mdl'
    NAME = 'Markdownlint'
    URL = 'https://github.com/markdownlint/markdownlint'

    EXAMPLE_CMD = """\
# Run Markdownlint and redirect the output to a file.
mdl /path/to/your/project > ./mdl_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Markdownlint.
report-converter -t mdl -o ./codechecker_mdl_reports ./mdl_reports.out

# Store the Markdownlint reports with CodeChecker.
CodeChecker store ./codechecker_mdl_reports -n mdl"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
