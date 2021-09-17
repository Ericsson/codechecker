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

from copy import deepcopy
from typing import Iterator, List, Tuple

from codechecker_report_converter.report import BugPathEvent, \
    get_or_create_file, Report
from ..parser import BaseParser


LOG = logging.getLogger('report-converter')


class Parser(BaseParser):
    """ Parser for clang-tidy console output. """

    def __init__(self):
        super(Parser, self).__init__()

        # Regex for parsing a clang-tidy message.
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
            # Checker name.
            r'\[(?P<checker>.*)\]')

        # Matches a note.
        self.note_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':' and a space.
            r'(?P<column>\d+?): '
            # Severity == note.
            r'note:'
            # Checker message.
            r'(?P<message>.*)')

    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[List[Report], str]:
        """ Parse the given line. """
        match = self.message_line_re.match(line)
        if match is None:
            return [], next(it)

        checker_names = match.group('checker').strip().split(",")
        report = Report(
            get_or_create_file(
                os.path.abspath(match.group('path')), self._file_cache),
            int(match.group('line')),
            int(match.group('column')),
            match.group('message').strip(),
            checker_names[0],
            bug_path_events=[])

        try:
            line = next(it)
            line = self._parse_code(it, line)
            line = self._parse_fixits(report, it, line)
            line = self._parse_notes(report, it, line)
        except StopIteration:
            line = ''
        finally:
            report.bug_path_events.append(BugPathEvent(
                report.message,
                report.file,
                report.line,
                report.column))

            # When a checker name and the alias of this checker is turned on,
            # Clang Tidy (>v11) will generate only one report where the checker
            # names are concatenated with ',' mark. With this we will generate
            # multiple reports for each checker name / alias.
            reports = []
            for checker_name in checker_names:
                r = deepcopy(report)
                r.checker_name = checker_name
                r.category = self._get_category(checker_name)

                reports.append(r)

            return reports, line

    def _get_category(self, checker_name: str) -> str:
        """ Get category for Clang-Tidy checker. """
        parts = checker_name.split('-')
        return parts[0] if parts else 'unknown'

    def _parse_code(
        self,
        it: Iterator[str],
        line: str
    ) -> str:
        # Eat code line.
        if self.note_line_re.match(line) or self.message_line_re.match(line):
            LOG.debug("Unexpected line: %s. Expected a code line!", line)
            return line

        # Eat arrow line.
        # FIXME: range support?
        line = next(it)
        if '^' not in line:
            LOG.debug("Unexpected line: %s. Expected an arrow line!", line)
            return line

        return next(it)

    def _parse_fixits(
        self,
        report: Report,
        it: Iterator[str],
        line: str
    ) -> str:
        """ Parses fixit messages. """

        while self.message_line_re.match(line) is None and \
                self.note_line_re.match(line) is None:
            message_text = line.strip()

            if message_text != '':
                report.bug_path_events.append(BugPathEvent(
                    f"{message_text} (fixit)",
                    report.file,
                    report.line,
                    line.find(message_text) + 1))

            line = next(it)
        return line

    def _parse_notes(
        self,
        report: Report,
        it: Iterator[str],
        line: str
    ) -> str:
        """ Parses note messages. """

        while self.message_line_re.match(line) is None:
            match = self.note_line_re.match(line)
            if match is None:
                LOG.debug("Unexpected line: %s", line)
                return next(it)

            report.bug_path_events.append(BugPathEvent(
                match.group('message').strip(),
                get_or_create_file(
                    os.path.abspath(match.group('path')), self._file_cache),
                int(match.group('line')),
                int(match.group('column'))))

            line = next(it)
            line = self._parse_code(it, line)
        return line
