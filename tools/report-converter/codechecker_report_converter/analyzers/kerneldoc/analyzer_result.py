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
    """ Transform analyzer result of kernel-docs. """

    TOOL_NAME = 'kernel-doc'
    NAME = 'Kernel-Doc'
    URL = 'https://github.com/torvalds/linux/blob/master/scripts/kernel-doc'

    EXAMPLE_CMD = """\
# Change directory to your kernel source repository.
cd path/to/linux/kernel/repository

# Run Kernel-Doc (via the Sphinx docs build) and redirect the output to a
# file.
make htmldocs 2>&1 | tee kernel-docs.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Kernel-Doc.
report-converter -t kernel-doc -o ./codechecker_kernel_doc_reports \
    ./kernel-docs.out

# Store the Kernel-Doc reports with CodeChecker.
CodeChecker store ./codechecker_kernel_doc_reports -n kernel-doc"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
