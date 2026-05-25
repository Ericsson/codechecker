# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import json
import logging
import os

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from codechecker_report_converter.report import BugPathEvent, File, \
    get_or_create_file, Range, Report

from ..analyzer_result import AnalyzerResultBase


LOG = logging.getLogger('report-converter')


CLIPPY_CHECKER = 'clippy'
RUSTC_CHECKER = 'rustc'


def actual_name_to_codechecker_name(checker_name: str) -> str:
    """
    Normalize Rust diagnostic codes to CodeChecker checker names.
    """
    if checker_name == CLIPPY_CHECKER:
        return CLIPPY_CHECKER

    if checker_name.startswith('clippy::'):
        return 'clippy-' + checker_name[len('clippy::'):].replace('_', '-')

    if checker_name.startswith('E') and checker_name[1:].isdigit():
        return f'{RUSTC_CHECKER}-{checker_name}'

    return f'{RUSTC_CHECKER}-' + checker_name.replace('_', '-')


class AnalyzerResult(AnalyzerResultBase):
    """
    Transform Cargo JSON diagnostics emitted by Clippy.
    """

    TOOL_NAME = CLIPPY_CHECKER
    NAME = 'Clippy'
    URL = 'https://github.com/rust-lang/rust-clippy'

    def get_reports(self, file_path: str) -> List[Report]:
        """
        Get reports from Cargo JSON message output.
        """
        if not os.path.isfile(file_path):
            LOG.error("Report file does not exist: %s", file_path)
            return []

        result_dir = os.path.dirname(os.path.abspath(file_path))
        file_cache: Dict[str, File] = {}
        reports: List[Report] = []

        for cargo_msg in self.__load_cargo_messages(file_path):
            if cargo_msg.get('reason') != 'compiler-message':
                continue

            diag = cargo_msg.get('message', {})
            if not isinstance(diag, dict):
                LOG.debug(
                    "Skipping cargo message with non-object diagnostic: %s",
                    file_path)
                continue

            report = self.__diagnostic_to_report(
                diag, cargo_msg, result_dir, file_cache)
            if report:
                reports.append(report)

        return reports

    def __load_cargo_messages(self, file_path: str) -> Iterable[Dict]:
        """
        Get JSON objects from Cargo's JSON-lines output.
        """
        try:
            with open(
                file_path, 'r', encoding='utf-8', errors='ignore'
            ) as output:
                for line_no, line in enumerate(output, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        msg = json.loads(line)
                        if isinstance(msg, dict):
                            yield msg
                        else:
                            LOG.debug(
                                "Skipping non-object cargo JSON at %s:%d.",
                                file_path, line_no)
                    except json.decoder.JSONDecodeError:
                        LOG.debug("Skipping non-JSON cargo output at %s:%d.",
                                  file_path, line_no)
        except OSError as ex:
            LOG.error("Failed to read the given analyzer result '%s'.",
                      file_path)
            LOG.error(ex)

    def __diagnostic_to_report(
        self,
        diag: Dict,
        cargo_msg: Dict,
        result_dir: str,
        file_cache: Dict[str, File]
    ) -> Optional[Report]:
        primary_span = self.__select_primary_span(diag.get('spans', []))
        if not primary_span:
            return None

        source_file = self.__resolve_span_file(
            primary_span, cargo_msg, result_dir)
        if not source_file:
            return None

        if not os.path.isfile(source_file):
            LOG.warning("Source file does not exist: %s", source_file)
            return None

        checker_name = self.__checker_name(diag)
        file = get_or_create_file(source_file, file_cache)
        rng = self.__span_range(primary_span)

        notes = self.__collect_notes(
            diag, primary_span, cargo_msg, result_dir, file_cache)

        return Report(
            file,
            rng.start_line,
            rng.start_col,
            self.__diagnostic_message(diag),
            checker_name,
            severity=self.__severity(diag.get('level')),
            bug_path_events=[
                BugPathEvent(
                    self.__diagnostic_message(diag),
                    file,
                    rng.start_line,
                    rng.start_col,
                    rng)
            ],
            notes=notes)

    def __select_primary_span(self, spans: Any) -> Optional[Dict]:
        if not isinstance(spans, list):
            return None

        for span in spans:
            if not isinstance(span, dict):
                continue

            if span.get('is_primary') and span.get('line_start'):
                return span

        for span in spans:
            if not isinstance(span, dict):
                continue

            if span.get('line_start'):
                return span

        return None

    def __collect_notes(
        self,
        diag: Dict,
        primary_span: Dict,
        cargo_msg: Dict,
        result_dir: str,
        file_cache: Dict[str, File]
    ) -> List[BugPathEvent]:
        notes: List[BugPathEvent] = []
        seen_notes: Set[Tuple[str, int, int, str]] = set()

        def append_note(note: Optional[BugPathEvent]) -> None:
            if not note:
                return

            key = (note.file.original_path, note.line,
                   note.column, note.message)
            if key not in seen_notes:
                seen_notes.add(key)
                notes.append(note)

        spans = diag.get('spans', [])
        if not isinstance(spans, list):
            spans = []

        for span in spans:
            if not isinstance(span, dict):
                continue

            if span is primary_span:
                continue

            note = self.__span_to_note(span, span.get('label'),
                                       cargo_msg, result_dir, file_cache)
            append_note(note)

        children = diag.get('children', [])
        if not isinstance(children, list):
            children = []

        for child in children:
            if not isinstance(child, dict):
                continue

            child_spans = child.get('spans', [])
            if not isinstance(child_spans, list):
                child_spans = []

            if child_spans:
                for span in child_spans:
                    if not isinstance(span, dict):
                        continue

                    note = self.__span_to_note(
                        span,
                        self.__child_message(child, span),
                        cargo_msg,
                        result_dir,
                        file_cache)
                    append_note(note)
            elif child.get('message'):
                primary_note = self.__span_to_note(
                    primary_span,
                    child.get('message'),
                    cargo_msg,
                    result_dir,
                    file_cache)
                append_note(primary_note)

        return notes

    def __span_to_note(
        self,
        span: Dict,
        msg: Optional[str],
        cargo_msg: Dict,
        result_dir: str,
        file_cache: Dict[str, File]
    ) -> Optional[BugPathEvent]:
        if not msg:
            return None

        source_file = self.__resolve_span_file(span, cargo_msg, result_dir)
        if not source_file:
            return None

        if not os.path.isfile(source_file):
            LOG.debug("Source file does not exist: %s", source_file)
            return None

        file = get_or_create_file(source_file, file_cache)
        rng = self.__span_range(span)

        return BugPathEvent(msg, file, rng.start_line, rng.start_col, rng)

    def __child_message(self, child: Dict, span: Dict) -> str:
        msg = child.get('message')
        if not isinstance(msg, str):
            msg = ''

        replacement = span.get('suggested_replacement')

        if isinstance(replacement, str) and replacement:
            return f'{msg} "{replacement}"'

        return msg

    def __span_range(self, span: Dict) -> Range:
        start_line = int(span.get('line_start') or 1)
        start_col = int(span.get('column_start') or 1)
        end_line = int(span.get('line_end') or start_line)
        end_col = int(span.get('column_end') or start_col)

        return Range(start_line, start_col, end_line, end_col)

    def __resolve_span_file(
        self,
        span: Dict,
        cargo_msg: Dict,
        result_dir: str
    ) -> Optional[str]:
        file_name = span.get('file_name')
        if not file_name or not isinstance(file_name, str):
            return None

        if os.path.isabs(file_name):
            return os.path.normpath(file_name)

        manifest_path = cargo_msg.get('manifest_path')
        if isinstance(manifest_path, str) and manifest_path:
            if not os.path.isabs(manifest_path):
                manifest_path = os.path.join(result_dir, manifest_path)

            return os.path.normpath(
                os.path.join(os.path.dirname(manifest_path), file_name))

        return os.path.normpath(os.path.join(result_dir, file_name))

    def __checker_name(self, diag: Dict) -> str:
        code = diag.get('code') or {}
        if isinstance(code, dict):
            diagnostic_code = code.get('code')
            if isinstance(diagnostic_code, str) and diagnostic_code:
                return actual_name_to_codechecker_name(diagnostic_code)

        if diag.get('level') == 'error':
            return RUSTC_CHECKER

        return CLIPPY_CHECKER

    def __diagnostic_message(self, diag: Dict) -> str:
        message = diag.get('message')

        return message if isinstance(message, str) else ''

    def __severity(self, level: Optional[str]) -> str:
        if level == 'error':
            return 'CRITICAL'

        if level == 'warning':
            return 'LOW'

        if level in ('note', 'help'):
            return 'STYLE'

        return 'UNSPECIFIED'
