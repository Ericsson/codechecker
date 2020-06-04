# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging

from codechecker_report_converter.analyzer_result import AnalyzerResult

from .output_parser import InferParser
from .plist_converter import InferPlistConverter


LOG = logging.getLogger('ReportConverter')


class InferAnalyzerResult(AnalyzerResult):
    """ Transform analyzer result of the FB Infer. """

    TOOL_NAME = 'fbinfer'
    NAME = 'Facebook Infer'
    URL = 'https://fbinfer.com'

    def parse(self, analyzer_result):
        """ Creates plist objects from the given analyzer result.

        Returns a list of plist objects.
        """
        parser = InferParser()
        messages = parser.parse_messages(analyzer_result)
        if not messages:
            return

        plist_converter = InferPlistConverter(self.TOOL_NAME)
        plist_converter.add_messages(messages)
        return plist_converter.get_plist_results()
