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

from ...output_parser import get_next, Message, Event
from ..output_parser import SANParser

LOG = logging.getLogger('ReportConverter')


class UBSANParser(SANParser):
    """ Parser for Clang UndefinedBehaviourSanitizer console outputs.

    Example output
        /a/b/main.cpp:13:10: runtime error: load of value 7...
    """

    def __init__(self):
        super(UBSANParser, self).__init__()

        # Regex for parsing UndefinedBehaviorSanitizer output message.
        self.ub_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':' and a space.
            r'(?P<column>\d+?): runtime error: '
            # Checker message.
            r'(?P<message>[\S \t]+)')

    def parse_stack_trace(self, it, line):
        """ Iterate over lines and parse stack traces. """
        events = []
        stack_traces = []

        while self.stack_trace_re.match(line):
            event = self.parse_stack_trace_line(line)
            if event:
                events.append(event)

            stack_traces.append(line)
            line = get_next(it)

        events.reverse()

        return stack_traces, events, line

    def parse_sanitizer_message(self, it, line):
        """ Parses UndefinedBehaviorSanitizer output message. """
        match = self.ub_line_re.match(line)
        if not match:
            return None, line

        report_file = os.path.abspath(match.group('path'))
        report_line = int(match.group('line'))
        report_col = int(match.group('column'))

        line = get_next(it)
        stack_traces, events, line = self.parse_stack_trace(it, line)

        notes = []
        if stack_traces:
            notes.append(Event(report_file, report_line, report_col,
                               ''.join(stack_traces)))

        return Message(report_file,
                       report_line,
                       report_col,
                       match.group('message').strip(),
                       'UndefinedBehaviorSanitizer',
                       events,
                       notes), line
