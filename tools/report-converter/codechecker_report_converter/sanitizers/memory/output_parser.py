# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import logging
import re

from ...output_parser import get_next, Message, Event
from ..output_parser import SANParser

LOG = logging.getLogger('ReportConverter')


class MSANParser(SANParser):
    """ Parser for Clang MemorySanitizer console outputs. """

    def __init__(self):
        super(MSANParser, self).__init__()

        # Regex for parsing MemorySanitizer output message.
        self.memory_line_re = re.compile(
            # Error code
            r'==(?P<code>\d+)==(ERROR|WARNING): MemorySanitizer: '
            # Checker message.
            r'(?P<message>[\S \t]+)')

    def parse_sanitizer_message(self, it, line):
        """ Parses MemorySanitizer output message.

        The first event will be the main location of the bug.
        """
        match = self.memory_line_re.match(line)
        if not match:
            return None, line

        line = get_next(it)
        stack_traces, events, line = self.parse_stack_trace(it, line)

        if not events:
            return None, line

        main_event = events[-1]

        notes = [Event(main_event.path, main_event.line, main_event.column,
                       ''.join(stack_traces))]

        return Message(main_event.path, main_event.line, main_event.column,
                       match.group('message').strip(),
                       "MemorySanitizer",
                       events, notes), line
