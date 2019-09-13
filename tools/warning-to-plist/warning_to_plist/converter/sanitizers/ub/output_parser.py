#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging
import os
import re

from ...output_parser import get_next, Message, Event, OutputParser

LOG = logging.getLogger('WarningToPlist')


class UBSANOutputParser(OutputParser):
    """ Parser for Clang UndefinedBehaviourSanitizer console outputs.

    Example output
        /a/b/main.cpp:13:10: runtime error: load of value 7...
    """

    def __init__(self):
        super(UBSANOutputParser, self).__init__()

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

        # Regex for parsing stack trace line.
        # It has the following format:
        #     #1 0x42a51d in main /dummy/main.cpp:24:2
        self.ub_stack_trace_re = re.compile(r'^\s+#\d+')

        self.file_re = re.compile(
            r'(?P<path>[\S]+?):(?P<line>\d+)(:(?P<column>\d+))?')

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        message, next_line = self.parse_sanitizer_message(it, line)
        if message:
            return message, next_line

        return None, next(it)

    def parse_sanitizer_message(self, it, line):
        """ Parses UndefinedBehaviorSanitizer output message. """
        match = self.ub_line_re.match(line)
        if not match:
            return None, line

        report_file = os.path.abspath(match.group('path'))
        report_line = int(match.group('line'))
        report_col = int(match.group('column'))

        events = []
        stack_traces = []

        line = get_next(it)

        # Read lines while it is a stack trace.
        while self.ub_stack_trace_re.match(line):
            file_match = self.file_re.search(line)
            if file_match:
                file_path = file_match.group('path')
                if file_path and os.path.exists(file_path):
                    events.append(Event(file_path,
                                        int(file_match.group('line')),
                                        int(file_match.group('column')),
                                        line.rstrip()))

            stack_traces.append(line)
            line = get_next(it)

        events.reverse()

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
