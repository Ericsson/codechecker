# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
from typing import List

from codechecker_report_converter.report import Report
from codechecker_report_converter.report.parser import sarif

from ..analyzer_result import AnalyzerResultBase


LOG = logging.getLogger('report-converter')


class AnalyzerResult(AnalyzerResultBase):
    """ Transform analyzer result of the GCC Static Analyzer. """

    TOOL_NAME = 'gcc'
    NAME = 'GNU Compiler Collection Static Analyzer'
    URL = 'https://gcc.gnu.org/wiki/StaticAnalyzer'

    EXAMPLE_CMD = """\
# Compile and analyze with GCC's static analyzer (GCC 13+), producing a
# sarif output file.
g++ -fanalyzer -fdiagnostics-format=sarif-file my_file.cpp

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of GCC's static analyzer.
report-converter -t gcc -o ./codechecker_gcc_reports my_file.cpp.sarif

# Store the gcc reports with CodeChecker.
CodeChecker store ./codechecker_gcc_reports -n gcc"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result file. """

        return sarif.Parser().get_reports(file_path)
