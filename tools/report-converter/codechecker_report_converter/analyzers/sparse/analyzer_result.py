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
    """ Transform analyzer result of Sparse. """

    TOOL_NAME = 'sparse'
    NAME = 'Sparse'
    URL = 'https://git.kernel.org/pub/scm/devel/sparse/sparse.git'

    EXAMPLE_CMD = """\
# Change directory to your kernel source repository.
cd path/to/linux/kernel/repository

# Run Sparse and redirect the output to a file.
make C=1 2>&1 | tee sparse.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Sparse.
report-converter -t sparse -o ./codechecker_sparse_reports ./sparse.out

# Store the Sparse reports with CodeChecker.
CodeChecker store ./codechecker_sparse_reports -n sparse"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
