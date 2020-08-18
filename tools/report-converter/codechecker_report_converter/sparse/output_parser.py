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

from ..output_parser import Message, Event, BaseParser

LOG = logging.getLogger('ReportConverter')


class SparseParser(BaseParser):
    """ Parser for sparse console output. """

    def __init__(self, analyzer_result):
        super(SparseParser, self).__init__()

        self.analyzer_result = analyzer_result

        # Regex for parsing a sparse message.
        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':' and a space.
            r'(?P<column>\d+?): '
            # Severity followed by a ':'.
            r'(?P<severity>(error|warning)):'
            # Checker message.
            r'(?P<message>[\S \t]+)\s*'
        )

        # Match a sparse note
        self.note_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':' , 4 spaces (not a tab because a 
            # tab has 7 spaces)
            r'(?P<column>\d+?):    '
            # Detailed info type followed by a ':'.
            r'(?P<severity>(expected|got|struct)) '
            # Checker message
            r'(?P<message>[\S \t]+)\s*'
        )

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        match = self.message_line_re.match(line)
        if match is None:
            return None, next(it)
        
        message_body = match.group('message').strip()
        file_path = os.path.normpath(
            os.path.join(os.path.dirname(self.analyzer_result), 
            match.group('path'))) 

        message = Message(
            file_path,
            int(match.group('line')),
            int(match.group('column')),
            message_body,
            "sparse")

        try:
            line = next(it)
            note_match = self.note_line_re.match(line)
            while note_match:
                file_path = os.path.normpath(
                    os.path.join(os.path.dirname(self.analyzer_result), 
                    note_match.group('path')))
                message.events.append(Event(file_path,
                                        int(note_match.group('line')),
                                        int(note_match.group('column')),
                                        note_match.group('severity').strip() + " " \
                                        + note_match.group('message').strip()))
                line = next(it)
                note_match = self.note_line_re.match(line)

            return message, line
        except StopIteration:
            return message, ''
