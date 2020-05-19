# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


from abc import abstractmethod

import logging
import os
import re

from ..output_parser import get_next, BaseParser, Event

LOG = logging.getLogger('ReportConverter')


class SANParser(BaseParser):
    """ Parser for Clang UndefinedBehaviourSanitizer console outputs.

    Example output
        /a/b/main.cpp:13:10: runtime error: load of value 7...
    """

    def __init__(self):
        super(SANParser, self).__init__()

        # Regex for parsing stack trace line.
        # It has the following format:
        #     #1 0x42a51d in main /dummy/main.cpp:24:2
        self.stack_trace_re = re.compile(r'^\s+#\d+')

        self.file_re = re.compile(
            r'(?P<path>[\S]+?):(?P<line>\d+)(:(?P<column>\d+))?')

    @abstractmethod
    def parse_sanitizer_message(self, it, line):
        """ Parse the given line. """
        raise NotImplementedError("Subclasses should implement this!")

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        message, next_line = self.parse_sanitizer_message(it, line)
        if message:
            return message, next_line

        return None, next(it)

    def parse_stack_trace_line(self, line):
        """ Parse the given stack trace line.

        Return an event if the file in the stack trace line exists otherwise
        it returns None.
        """
        file_match = self.file_re.search(line)
        if not file_match:
            return None

        file_path = file_match.group('path')
        if file_path and os.path.exists(file_path):
            col = file_match.group('column')
            return Event(os.path.abspath(file_path),
                         int(file_match.group('line')),
                         int(col) if col else 0,
                         line.rstrip())

        return None

    def parse_stack_trace(self, it, line):
        """ Iterate over lines and parse stack traces. """
        events = []
        stack_traces = []

        while line.strip():
            event = self.parse_stack_trace_line(line)
            if event:
                events.append(event)

            stack_traces.append(line)
            line = get_next(it)

        events.reverse()

        return stack_traces, events, line
