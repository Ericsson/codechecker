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


class ClangTidyParser(BaseParser):
    """ Parser for clang-tidy console output. """

    def __init__(self):
        super(ClangTidyParser, self).__init__()

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

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        match = self.message_line_re.match(line)
        if match is None:
            return None, next(it)

        message = Message(
            os.path.abspath(match.group('path')),
            int(match.group('line')),
            int(match.group('column')),
            match.group('message').strip(),
            match.group('checker').strip())

        try:
            line = next(it)
            line = self._parse_code(message, it, line)
            line = self._parse_fixits(message, it, line)
            line = self._parse_notes(message, it, line)

            return message, line
        except StopIteration:
            return message, ''

    def _parse_code(self, message, it, line):
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

    def _parse_fixits(self, message, it, line):
        """ Parses fixit messages. """

        while self.message_line_re.match(line) is None and \
                self.note_line_re.match(line) is None:
            message_text = line.strip()

            if message_text != '':
                message.fixits.append(Event(message.path, message.line,
                                            line.find(message_text) + 1,
                                            message_text))
            line = next(it)
        return line

    def _parse_notes(self, message, it, line):
        """ Parses note messages. """

        while self.message_line_re.match(line) is None:
            match = self.note_line_re.match(line)
            if match is None:
                LOG.debug("Unexpected line: %s", line)
                return next(it)

            message.events.append(Event(os.path.abspath(match.group('path')),
                                        int(match.group('line')),
                                        int(match.group('column')),
                                        match.group('message').strip()))
            line = next(it)
            line = self._parse_code(message, it, line)
        return line
