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

from codechecker_report_converter.report import get_or_create_file, Report
from ..parser import BaseParser


LOG = logging.getLogger('report-converter')


class Parser(BaseParser):
    """ Parser for Pyflakes output. """

    def __init__(self, analyzer_result):
        super(Parser, self).__init__()

        self.analyzer_result = analyzer_result

        # Regex for parsing a clang-tidy message.
        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Message.
            r'(?P<message>[\S \t]+)\s*')

    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[List[Report], str]:
        """ Parse the given line. """
        match = self.message_line_re.match(line)
        if match is None:
            return [], next(it)

        file_path = os.path.join(os.path.dirname(self.analyzer_result),
                                 match.group('path'))

        report = Report(
            get_or_create_file(file_path, self._file_cache),
            int(match.group('line')),
            0,
            match.group('message').strip(),
            '')

        try:
            return [report], next(it)
        except StopIteration:
            return [report], ''
