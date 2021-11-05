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
    """
    Parser for Coccinelle Output
    """

    def __init__(self, analyzer_result: str):
        super(Parser, self).__init__()

        self.analyzer_result = analyzer_result
        self.checker_name: str = ''

        self.checker_name_re = re.compile(
            r'^Processing (?P<checker_name>[\S ]+)\.cocci$'
        )

        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # A range of column numbers, only start to be used
            r'(?P<column>(\d+?))-(\d+?):'
            # Message.
            r'(?P<message>[\S \t]+)\s*')

    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[List[Report], str]:
        """ Parse the given line. """
        match = self.message_line_re.match(line)

        checker_match = self.checker_name_re.match(line)
        if checker_match:
            self.checker_name = 'coccinelle.' + \
                checker_match.group('checker_name')

        if match is None:
            return [], next(it)

        file_path = os.path.normpath(
            os.path.join(os.path.dirname(self.analyzer_result),
                         match.group('path')))

        report = Report(
            get_or_create_file(file_path, self._file_cache),
            int(match.group('line')),
            int(match.group('column')),
            match.group('message').strip(),
            self.checker_name)

        try:
            return [report], next(it)
        except StopIteration:
            return [report], ''
