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

    def __init__(self):
        super(AnalyzerResult, self).__init__()

    def get_reports(self, result_file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result file. """

        return sarif.Parser().get_reports(result_file_path)
