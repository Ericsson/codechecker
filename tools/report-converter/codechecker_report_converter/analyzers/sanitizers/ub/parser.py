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

from typing import Iterable, Optional, Tuple

from codechecker_report_converter.report import get_or_create_file, Report

from ...parser import get_next
from ..parser import SANParser


LOG = logging.getLogger('report-converter')


class Parser(SANParser):
    """ Parser for Clang UndefinedBehaviourSanitizer console outputs.

    Example output
        /a/b/main.cpp:13:10: runtime error: load of value 7...
    """

    checker_name = "UndefinedBehaviorSanitizer"

    # Regex for parsing UndefinedBehaviorSanitizer output message.
    line_re = re.compile(
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

    def parse_sanitizer_message(
        self,
        it: Iterable[str],
        line: str
    ) -> Tuple[Optional[Report], str]:
        """ Parses UndefinedBehaviorSanitizer output message. """
        match = self.line_re.match(line)
        if not match:
            return None, line

        report_file = get_or_create_file(
            os.path.abspath(match.group('path')), self._file_cache)
        report_line = int(match.group('line'))
        report_col = int(match.group('column'))

        line = get_next(it)
        stack_traces, events, line = self.parse_stack_trace(it, line)

        report = self.create_report(
            events, report_file, report_line, report_col,
            match.group('message').strip(), stack_traces)

        return report, line
