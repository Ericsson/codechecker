# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


from codechecker_report_converter.analyzer_result import AnalyzerResult

from .output_parser import ClangTidyParser
from .plist_converter import ClangTidyPlistConverter


class ClangTidyAnalyzerResult(AnalyzerResult):
    """ Transform analyzer result of Clang Tidy. """

    TOOL_NAME = 'clang-tidy'
    NAME = 'Clang Tidy'
    URL = 'https://clang.llvm.org/extra/clang-tidy'

    def parse(self, analyzer_result):
        """ Creates plist files from the given analyzer result to the given
        output directory.
        """
        parser = ClangTidyParser()

        content = self._get_analyzer_result_file_content(analyzer_result)
        if not content:
            return

        messages = parser.parse_messages(content)

        plist_converter = ClangTidyPlistConverter(self.TOOL_NAME)
        plist_converter.add_messages(messages)
        return plist_converter.get_plist_results()
