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

from typing import Iterator, List, Tuple

from codechecker_report_converter.report import BugPathEvent, \
    get_or_create_file, Report
from ..parser import BaseParser


LOG = logging.getLogger('report-converter')


class Parser(BaseParser):
    """
    Parser for Sparse Output
    """

    def __init__(self, analyzer_result):
        super(Parser, self).__init__()

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

    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[List[Report], str]:
        """ Parse the given line. """
        match = self.message_line_re.match(line)

        if (match is None):
            return [], next(it)

        file_path = os.path.normpath(
            os.path.join(os.path.dirname(self.analyzer_result),
                         match.group('path')))

        report = Report(
            get_or_create_file(file_path, self._file_cache),
            int(match.group('line')),
            int(match.group('column')),
            match.group('message').strip(),
            '',
            bug_path_events=[])

        line = ''
        try:
            line = next(it)
            note_match = self.note_line_re.match(line)
            while note_match:
                file_path = os.path.normpath(
                    os.path.join(os.path.dirname(self.analyzer_result),
                                 note_match.group('path')))

                report.bug_path_events.append(BugPathEvent(
                    note_match.group('message').strip(),
                    get_or_create_file(file_path, self._file_cache),
                    int(note_match.group('line')),
                    int(note_match.group('column'))))

                line = next(it)
                note_match = self.note_line_re.match(line)
        except StopIteration:
            line = ''
        finally:
            report.bug_path_events.append(BugPathEvent(
                report.message,
                report.file,
                report.line,
                report.column))

            return [report], line
