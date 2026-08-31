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
    """ Transform analyzer result of Pyflakes. """

    TOOL_NAME = 'pyflakes'
    NAME = 'Pyflakes'
    URL = 'https://github.com/PyCQA/pyflakes'

    EXAMPLE_CMD = """\
# Run Pyflakes and redirect the output to a file.
pyflakes /path/to/your/project > ./pyflakes_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Pyflakes.
report-converter -t pyflakes -o ./codechecker_pyflakes_reports \
    ./pyflakes_reports.out

# Store the Pyflakes reports with CodeChecker.
CodeChecker store ./codechecker_pyflakes_reports -n pyflakes"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
