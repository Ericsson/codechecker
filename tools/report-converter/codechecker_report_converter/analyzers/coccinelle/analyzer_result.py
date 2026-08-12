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
    """ Transform analyzer result of Coccinelle. """

    TOOL_NAME = 'coccinelle'
    NAME = 'Coccinelle'
    URL = 'https://github.com/coccinelle/coccinelle'

    EXAMPLE_CMD = """\
# Change directory to your project (e.g. the Linux kernel).
cd path/to/linux/kernel/repository

# Run Coccicheck and redirect the output to a file.
make coccicheck MODE=report V=1 > ./coccinelle_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Coccinelle.
report-converter -t coccinelle -o ./codechecker_coccinelle_reports \
    ./coccinelle_reports.out

# Store the Coccinelle reports with CodeChecker.
CodeChecker store ./codechecker_coccinelle_reports -n coccinelle"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
