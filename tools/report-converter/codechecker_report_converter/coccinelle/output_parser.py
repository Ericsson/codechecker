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


class CoccinelleParser(BaseParser):
    """
    Parser for Coccinelle Output
    """

    def __init__(self, analyzer_result):
        super(CoccinelleParser, self).__init__()

        self.analyzer_result = analyzer_result
        self.checker_name = None

        self.checker_name_re = re.compile(
            r'^Processing (?P<checker_name>[\S ]+)\.cocci$'
        )

        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # A range of column numbers, only start to be used
            r'(?P<column>(\d+?))-(\d+?):'
            # Message.
            r'(?P<message>[\S \t]+)\s*')

    def parse_message(self, it, line):
        """
        Actual Parsing function for the given line
        """
        match = self.message_line_re.match(line)

        checker_match = self.checker_name_re.match(line)
        if checker_match:
            self.checker_name = 'coccinelle.' + \
                checker_match.group('checker_name')

        if match is None:
            return None, next(it)

        file_path = os.path.normpath(
            os.path.join(os.path.dirname(self.analyzer_result),
                         match.group('path')))

        message = Message(
            file_path,
            int(match.group('line')),
            int(match.group('column')),
            match.group('message').strip(),
            self.checker_name)

        try:
            return message, next(it)
        except StopIteration:
            return message, ''
