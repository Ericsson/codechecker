# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import os

from abc import ABCMeta, abstractmethod
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from codechecker_report_converter.report import File, Report


LOG = logging.getLogger('report-converter')


def get_next(it):
    """ Returns the next item from the iterator or return an empty string. """
    try:
        return next(it)
    except StopIteration:
        return ''


class BaseParser(metaclass=ABCMeta):
    """ Warning message parser. """

    def __init__(self):
        self.reports: List[Report] = []
        self._file_cache: Dict[str, File] = {}

    def get_reports(self, file_path: str) -> List[Report]:
        """ Parse the given output. """
        lines = self._get_analyzer_result_file_content(file_path)
        if not lines:
            return self.reports

        return self.get_reports_from_iter(lines)

    def get_reports_from_iter(self, lines: Iterable[str]) -> List[Report]:
        """ Parse the given output lines. """
        it = iter(lines)
        try:
            next_line = next(it)
            while True:
                reports, next_line = self._parse_line(it, next_line)
                if reports:
                    self.reports.extend(reports)
        except StopIteration:
            pass

        return self.reports

    def _get_analyzer_result_file_content(
        self,
        result_file_path: str
    ) -> Optional[List[str]]:
        """ Return the content of the given file. """
        if not os.path.exists(result_file_path):
            LOG.error("Result file does not exists: %s", result_file_path)
            return None

        if os.path.isdir(result_file_path):
            LOG.error("Directory is given instead of a file: %s",
                      result_file_path)
            return None

        with open(result_file_path, 'r', encoding='utf-8',
                  errors='replace') as analyzer_result:
            return analyzer_result.readlines()

    @abstractmethod
    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[List[Report], str]:
        """ Parse the given line. """
        raise NotImplementedError("Subclasses should implement this!")
