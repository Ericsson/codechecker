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

from typing import Iterator, List, Optional, Tuple

from codechecker_report_converter.report import BugPathEvent, File, \
    get_or_create_file, Report

from ..parser import get_next, BaseParser

LOG = logging.getLogger('report-converter')


class SANParser(BaseParser):
    """ Parser for Clang UndefinedBehaviourSanitizer console outputs.

    Example output
        /a/b/main.cpp:13:10: runtime error: load of value 7...
    """

    checker_name: str = ""
    main_event_index = -1
    line_re = re.compile(r'')

    def __init__(self):
        super(SANParser, self).__init__()

        # Regex for parsing stack trace line.
        # It has the following format:
        #     #1 0x42a51d in main /dummy/main.cpp:24:2
        self.stack_trace_re = re.compile(r'^\s+#\d+')

        self.file_re = re.compile(
            r'(?P<path>[\S]+?):(?P<line>\d+)(:(?P<column>\d+))?')

    def parse_sanitizer_message(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[Optional[Report], str]:
        """ Parses ThreadSanitizer output message. """
        match = self.line_re.match(line)
        if not match:
            return None, line

        line = get_next(it)
        stack_traces, events, line = self.parse_stack_trace(it, line)

        if not events:
            return None, line

        main_event = events[self.main_event_index]

        report = self.create_report(
            events, main_event.file, main_event.line, main_event.column,
            match.group('message').strip(), stack_traces)

        return report, line

    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[List[Report], str]:
        """ Parse the given line. """
        report, next_line = self.parse_sanitizer_message(it, line)
        if report:
            return [report], next_line

        return [], next(it)

    def parse_stack_trace_line(self, line: str) -> Optional[BugPathEvent]:
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
            return BugPathEvent(
                line.rstrip(),
                get_or_create_file(
                    os.path.abspath(file_path), self._file_cache),
                int(file_match.group('line')),
                int(col) if col else 0)

        return None

    def create_report(
        self,
        events: List[BugPathEvent],
        file: File,
        line: int,
        column: int,
        message: str,
        stack_traces: List[str]
    ) -> Report:
        """ Create a report for the sanitizer output. """
        # The original message should be the last part of the path. This is
        # displayed by quick check, and this is the main event displayed by
        # the web interface.
        events.append(BugPathEvent(message, file, line, column))

        notes = None
        if stack_traces:
            notes = [BugPathEvent(''.join(stack_traces), file, line, column)]

        return Report(
            file, line, column, message, self.checker_name,
            bug_path_events=events,
            notes=notes)

    def parse_stack_trace(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[List[str], List[BugPathEvent], str]:
        """ Iterate over lines and parse stack traces. """
        events: List[BugPathEvent] = []
        stack_traces: List[str] = []

        while line.strip():
            event = self.parse_stack_trace_line(line)
            if event:
                events.append(event)

            stack_traces.append(line)
            line = get_next(it)

        events.reverse()

        return stack_traces, events, line
