# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from codechecker_report_converter.analyzer_result import AnalyzerResult

from .output_parser import MarkdownlintParser
from ..plist_converter import PlistConverter


class MarkdownlintAnalyzerResult(AnalyzerResult):
    """ Transform analyzer result of Markdownlint. """

    TOOL_NAME = 'mdl'
    NAME = 'Markdownlint'
    URL = 'https://github.com/markdownlint/markdownlint'

    def parse(self, analyzer_result):
        """ Creates plist data from the given analyzer results. """
        parser = MarkdownlintParser(analyzer_result)

        content = self._get_analyzer_result_file_content(analyzer_result)
        if not content:
            return

        messages = parser.parse_messages(content)

        plist_converter = PlistConverter(self.TOOL_NAME)
        plist_converter.add_messages(messages)
        return plist_converter.get_plist_results()
