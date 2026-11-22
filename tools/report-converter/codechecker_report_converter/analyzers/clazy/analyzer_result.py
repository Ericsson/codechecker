# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from codechecker_report_converter.report import Report

from ..analyzer_result import AnalyzerResultBase
from .parser import Parser


class AnalyzerResult(AnalyzerResultBase):
    """ Transform analyzer result of clazy. """

    TOOL_NAME = 'clazy'
    NAME = 'Clazy'
    URL = 'https://invent.kde.org/sdk/clazy'

    EXAMPLE_CMD = """\
# Run clazy-standalone and redirect its output (written to stderr) to a file.
clazy-standalone --checks=level1 -p ./build my_file.cpp \\
    > ./clazy_reports.out 2>&1

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of clazy.
report-converter -t clazy -o ./codechecker_clazy_reports ./clazy_reports.out

# Store the clazy reports with CodeChecker.
CodeChecker store ./codechecker_clazy_reports -n clazy"""

    def get_reports(self, file_path: str) -> list[Report]:
        """ Get reports from the given analyzer result. """
        return Parser().get_reports(file_path)
