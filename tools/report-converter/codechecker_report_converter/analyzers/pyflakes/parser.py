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

from typing import Iterator

from codechecker_report_converter.report import get_or_create_file, Report
from ..parser import BaseParser


LOG = logging.getLogger('report-converter')


class Parser(BaseParser):
    """ Parser for Pyflakes output. """

    def __init__(self, analyzer_result):
        super().__init__()

        self.analyzer_result = analyzer_result

        # Regex for parsing a Pyflakes message.
        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Optional column number. Pyflakes 2.2.0 to 2.4.0 print it
            # followed by a space, later versions followed by ':'. Older
            # versions do not print it.
            r'(?:(?P<column>\d+):?(?=\s))?'
            # Message.
            r'(?P<message>[\S \t]+)\s*')

    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> tuple[list[Report], str]:
        """ Parse the given line. """
        match = self.message_line_re.match(line)
        if match is None:
            return [], next(it)

        file_path = os.path.join(os.path.dirname(self.analyzer_result),
                                 match.group('path'))

        report = Report(
            get_or_create_file(file_path, self._file_cache),
            int(match.group('line')),
            int(match.group('column') or 0),
            match.group('message').strip(),
            '')

        try:
            return [report], next(it)
        except StopIteration:
            return [report], ''
