# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import os
import re

from ..output_parser import BaseParser, Message
LOG = logging.getLogger('ReportConverter')


class SmatchParser(BaseParser):
    """
    Parser for Smatch Output
    """

    def __init__(self, analyzer_result):
        super(SmatchParser, self).__init__()

        self.analyzer_result = analyzer_result

        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a whitespace.
            r'(?P<line>\d+?)\s'
            # Function name followed by a whitespace.
            r'(?P<function_name>\S+)\s'
            # Checker name followed by a whitespace
            r'\[(?P<checker_name>smatch\.\S+)\]\s'
            # Message.
            r'(?P<message>[\S \t]+)\s*')

    def parse_message(self, it, line):
        """
        Actual Parsing function for the given line
        It is expected that each line contains a seperate report
        """
        match = self.message_line_re.match(line)
        if match is None:
            return None, next(it)

        file_path = os.path.normpath(
            os.path.join(os.path.dirname(self.analyzer_result),
                         match.group('path')))

        column = 0

        message = Message(
            file_path,
            int(match.group('line')),
            column,
            match.group('message').strip(),
            match.group('checker_name'))

        try:
            return message, next(it)
        except StopIteration:
            return message, ''
