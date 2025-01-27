# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import yaml
import logging
from typing import Iterator, List, Tuple

from codechecker_report_converter.report import BugPathEvent, \
    get_or_create_file, Report

from ..parser import BaseParser

LOG = logging.getLogger('report-converter')


def get_location_by_offset(filename, offset):
    """
    This function returns the line and column number in the given file which
    is located at the given offset (i.e. number of characters including new
    line characters). None returns when the offset is greater than the file
    length.
    """
    with open(filename, encoding='utf-8', errors='ignore', newline='') as f:
        for row, line in enumerate(f, 1):
            length = len(line)
            if length < offset:
                offset -= length
            else:
                return row, offset + 1

    return None


class Parser(BaseParser):
    """Parser for clang-tidy YAML output."""

    def get_reports(self, file_path: str) -> List[Report]:
        """Parse Clang-Tidy's YAML output file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

        reports = []
        if data:
            for diagnostic in data['Diagnostics']:
                report = self._parse_diagnostic(diagnostic)
                reports.append(report)
        return reports

    def _parse_diagnostic(self, diagnostic: dict) -> Report:
        """Parse a Clang-Tidy diagnostic."""
        checker_name = diagnostic.get('DiagnosticName', '')
        diagnostic_message = diagnostic.get('DiagnosticMessage', {})
        file_path = os.path.abspath(diagnostic_message['FilePath'])
        file_obj = get_or_create_file(file_path, self._file_cache)
        line, col = get_location_by_offset(
            file_path, diagnostic_message.get('FileOffset'))

        report = Report(
            file=file_obj,
            line=line,
            column=col,
            message=diagnostic_message.get('Message', '').strip(),
            checker_name=checker_name,
            category=self._get_category(checker_name),
            bug_path_events=[]
        )

        # Parse replacements (fixits) (if any)
        for replacement in diagnostic_message.get('Replacements', []):
            replacement_path = os.path.abspath(replacement['FilePath'])
            replacement_file_obj = get_or_create_file(replacement_path,
                                                      self._file_cache)
            fixit_line, fixit_col = get_location_by_offset(
                replacement_path, replacement['Offset'])
            report.notes.append(
                BugPathEvent(
                    f"{replacement['ReplacementText']} (fixit)",
                    replacement_file_obj,
                    fixit_line,
                    fixit_col
                )
            )

        # Parse notes (if any)
        for note in diagnostic.get('Notes', []):
            if note['FilePath'] != '':
                note_path = os.path.abspath(note['FilePath'])
                note_line, note_col = get_location_by_offset(
                    note_path, note['FileOffset'])
                note_file_obj = get_or_create_file(note_path, self._file_cache)
                report.bug_path_events.append(
                    BugPathEvent(
                        note['Message'].strip(),
                        note_file_obj,
                        note_line,
                        note_col
                    )
                )

        report.bug_path_events.append(BugPathEvent(
            report.message,
            report.file,
            report.line,
            report.column))

        return report

    def _get_category(self, checker_name: str) -> str:
        """ Get category for Clang-Tidy checker. """
        parts = checker_name.split('-')
        return parts[0] if parts else 'unknown'

    def _parse_line(self, it: Iterator[str], line: str) -> Tuple[
            List[Report], str]:
        # FIXME: This method is a placeholder to allow instantiation of the
        #  Parser class.
        # The _parse_line method is required because Parser is an abstract
        # class that expects this method to be implemented in subclasses.
        return [], ""
