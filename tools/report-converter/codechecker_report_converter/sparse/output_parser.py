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

from ..output_parser import BaseParser, Message, Event
LOG = logging.getLogger('ReportConverter')


class SparseParser(BaseParser):
    """
    Parser for Sparse Output
    """

    def __init__(self, analyzer_result):
        super(SparseParser, self).__init__()

        self.analyzer_result = analyzer_result

        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':'.
            r'(?P<column>\d+?):'
            # Message.
            r'(?P<message>[\S \t]+)\s*')

        self.note_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>\.[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':'.
            r'(?P<column>\d+?):'
            # Message.
            r'(?P<message>[\S \t]+)\s*'
        )

    def parse_message(self, it, line):
        """
        Actual Parsing function for the given line
        It is expected that each line contains a seperate report
        """
        match = self.message_line_re.match(line)

        if (match is None):
            return None, next(it)

        checker_name = None

        file_path = os.path.normpath(
            os.path.join(os.path.dirname(self.analyzer_result),
                         match.group('path')))
        message = Message(
            file_path,
            int(match.group('line')),
            int(match.group('column')),
            match.group('message').strip(),
            checker_name)

        try:
            line = next(it)
            note_match = self.note_line_re.match(line)
            while note_match:
                file_path = os.path.normpath(
                    os.path.join(os.path.dirname(self.analyzer_result),
                                 note_match.group('path')))
                message.events.append(Event(file_path,
                                            int(note_match.group('line')),
                                            int(note_match
                                                .group('column')),
                                            note_match.group('message')
                                            .strip()))
                line = next(it)
                note_match = self.note_line_re.match(line)
            return message, line

        except StopIteration:
            return message, ''
