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
    """ Transform analyzer result of Clang AddressSanitizer. """

    TOOL_NAME = 'asan'
    NAME = 'AddressSanitizer'
    URL = 'https://clang.llvm.org/docs/AddressSanitizer.html'

    EXAMPLE_CMD = """\
# Compile your program with debug info and a frame pointer.
clang++ -fsanitize=address -g -fno-omit-frame-pointer asan.cpp

# Run your program and redirect the output to a file.
ASAN_SYMBOLIZER_PATH=/usr/lib/llvm-6.0/bin/llvm-symbolizer \\
./a.out > asan.output 2>&1

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of AddressSanitizer.
report-converter -t asan -o ./asan_results asan.output"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser().get_reports(file_path)
