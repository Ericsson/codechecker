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


class LSANParser(SANParser):
    """ Parser for Clang LeakSanitizer console outputs. """

    def __init__(self):
        super(LSANParser, self).__init__()

        # Regex for parsing MemorySanitizer output message.
        self.leak_line_re = re.compile(
            # Error code
            r'==(?P<code>\d+)==(ERROR|WARNING): LeakSanitizer: '
            # Checker message.
            r'(?P<message>[\S \t]+)')

    def parse_sanitizer_message(self, it, line):
        """ Parses LeakSanitizer output message.

        The first event will be the main location of the bug.
        """
        match = self.leak_line_re.match(line)
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
                       "LeakSanitizer",
                       events, notes), line
