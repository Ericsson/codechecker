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
    """ Transform analyzer result of the JSCPD analyzer. """

    TOOL_NAME = 'jscpd'
    NAME = 'JSCPD'
    URL = 'https://www.npmjs.com/package/jscpd'

    EXAMPLE_CMD = """\
# Run jscpd and generate a json report.
jscpd --reporters json -o ./jscpd_reports /path/to/my/project

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of jscpd.
report-converter -t jscpd -o ./codechecker_jscpd_reports \
    ./jscpd_reports/jscpd-report.json

# Store the jscpd reports with CodeChecker.
CodeChecker store ./codechecker_jscpd_reports -n jscpd"""

    def get_reports(self, file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        return Parser().get_reports(file_path)
