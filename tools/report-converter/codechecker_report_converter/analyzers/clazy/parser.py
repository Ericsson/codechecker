# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import re

from typing import Iterable, Iterator

from codechecker_report_converter.report import Report
from ..clang_tidy.parser import Parser as ClangTidyParser


# Lines that clang prints around the diagnostics. These are not part of any
# diagnostic, so they would otherwise be parsed as fixit lines.
IGNORED_LINE_RES = [
    re.compile(r'^In file included from .+:\d+:$'),
    re.compile(r'^\d+ (warning|error)s?( and \d+ errors?)? generated\.$'),
    re.compile(r'^Error while processing .+\.$')]

# A compile error has no checker name at the end of the line.
ERROR_LINE_RE = re.compile(
    r'^(?P<location>[\S ]+?:\d+:\d+: )(fatal )?error: (?P<message>.*)$')

CHECKER_NAME_RE = re.compile(r'\[[^\[\]\s]+\]$')


def get_checker_name(diagnostic_flag: str) -> str:
    """
    Get the CodeChecker checker name of a diagnostic flag. Clazy checks are
    printed as -Wclazy-<check>, compiler warnings as -W<warning>. The latter
    are named like Clang-Tidy names them.
    """
    if diagnostic_flag.startswith('-Wclazy-'):
        return diagnostic_flag[len('-W'):]

    if diagnostic_flag.startswith('-W'):
        return 'clang-diagnostic-' + diagnostic_flag[len('-W'):]

    return diagnostic_flag


class Parser(ClangTidyParser):
    """ Parser for clazy-standalone console output. """

    def get_reports_from_iter(self, lines: Iterable[str]) -> list[Report]:
        """ Parse the given output lines. """
        return super().get_reports_from_iter(self.__preprocess(lines))

    def __preprocess(self, lines: Iterable[str]) -> Iterator[str]:
        """
        Remove the lines which do not belong to any diagnostic and rewrite
        compile errors to the format that the Clang-Tidy parser accepts.
        """
        for line in lines:
            stripped = line.rstrip('\r\n')

            if any(r.match(stripped) for r in IGNORED_LINE_RES):
                continue

            match = ERROR_LINE_RE.match(stripped)
            if match:
                message = match.group('message')
                if CHECKER_NAME_RE.search(message):
                    # A warning turned into an error by -Werror is printed
                    # as [-Werror,-W<warning>].
                    message = message.replace('[-Werror,', '[', 1)
                else:
                    message += ' [clang-diagnostic-error]'

                line = f"{match.group('location')}error: {message}\n"

            yield line

    def _parse_line(
        self,
        it: Iterator[str],
        line: str
    ) -> tuple[list[Report], str]:
        """ Parse the given line. """
        reports, line = super()._parse_line(it, line)

        for report in reports:
            report.checker_name = get_checker_name(report.checker_name)
            report.category = self._get_category(report.checker_name)

        return reports, line
