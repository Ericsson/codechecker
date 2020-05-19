# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from codechecker_report_converter.analyzer_result import AnalyzerResult

from .output_parser import SpotBugsParser
from .plist_converter import SpotBugsPlistConverter


class SpotBugsAnalyzerResult(AnalyzerResult):
    """ Transform analyzer result of SpotBugs. """

    TOOL_NAME = 'spotbugs'
    NAME = 'spotbugs'
    URL = 'https://spotbugs.github.io'

    def parse(self, analyzer_result):
        """ Creates plist files from the given analyzer result to the given
        output directory.
        """
        parser = SpotBugsParser()
        messages = parser.parse_messages(analyzer_result)
        if not messages:
            return None

        plist_converter = SpotBugsPlistConverter(self.TOOL_NAME)
        plist_converter.add_messages(messages)
        return plist_converter.get_plist_results()
