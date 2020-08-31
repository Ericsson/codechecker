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

from ..output_parser import Message, BaseParser

LOG = logging.getLogger('ReportConverter')


class MarkdownlintParser(BaseParser):
    """ Parser for Markdownlint output. """

    def __init__(self, analyzer_result):
        super(MarkdownlintParser, self).__init__()

        self.analyzer_result = analyzer_result

        # Regex for parsing a clang-tidy message.
        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?): '
            # Checker name.
            r'(?P<checker>[\S]+) '
            # Message.
            r'(?P<message>[\S \t]+)\s*')

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        match = self.message_line_re.match(line)
        if match is None:
            return None, next(it)

        file_path = os.path.normpath(
            os.path.join(os.path.dirname(self.analyzer_result),
                         match.group('path')))

        message = Message(
            file_path,
            int(match.group('line')),
            0,
            match.group('message').strip(),
            match.group('checker').strip())

        try:
            return message, next(it)
        except StopIteration:
            return message, ''
