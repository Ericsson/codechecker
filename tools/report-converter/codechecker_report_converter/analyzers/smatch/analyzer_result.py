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
    """ Transform analyzer result of Smatch. """

    TOOL_NAME = 'smatch'
    NAME = 'Smatch'
    URL = 'https://repo.or.cz/w/smatch.git'

    EXAMPLE_CMD = """\
# Change directory to your kernel source repository.
cd path/to/linux/kernel/repository

# Run Smatch (warnings are written to smatch_warns.txt by default).
path/to/smatch/smatch_scripts/test_kernel.sh

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Smatch.
report-converter -t smatch -o ./codechecker_smatch_reports ./smatch_warns.txt

# Store the Smatch reports with CodeChecker.
CodeChecker store ./codechecker_smatch_reports -n smatch"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser(file_path).get_reports(file_path)
