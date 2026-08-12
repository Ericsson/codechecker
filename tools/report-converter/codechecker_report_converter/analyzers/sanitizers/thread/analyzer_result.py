# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from typing import List

from codechecker_report_converter.report import Report

from ...analyzer_result import AnalyzerResultBase
from .parser import Parser


class AnalyzerResult(AnalyzerResultBase):
    """ Transform analyzer result of Clang ThreadSanitizer. """

    TOOL_NAME = 'tsan'
    NAME = 'ThreadSanitizer'
    URL = 'https://clang.llvm.org/docs/ThreadSanitizer.html'

    EXAMPLE_CMD = """\
# Compile your program with debug info.
clang++ -fsanitize=thread -g tsan.cpp

# Run your program and redirect the output to a file.
./a.out > tsan.output 2>&1

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of ThreadSanitizer.
report-converter -t tsan -o ./tsan_results tsan.output"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser().get_reports(file_path)
