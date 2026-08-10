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
    """ Transform analyzer result of Sphinx. """

    TOOL_NAME = 'sphinx'
    NAME = 'Sphinx'
    URL = 'https://github.com/sphinx-doc/sphinx'

    EXAMPLE_CMD = """\
# Change directory to your kernel source repository.
cd path/to/linux/kernel/repository

# Run Sphinx and redirect the output to a file.
make htmldocs 2>&1 | tee sphinx.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Sphinx.
report-converter -t sphinx -o ./codechecker_sphinx_reports ./sphinx.out

# Store the Sphinx reports with CodeChecker.
CodeChecker store ./codechecker_sphinx_reports -n sphinx"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
