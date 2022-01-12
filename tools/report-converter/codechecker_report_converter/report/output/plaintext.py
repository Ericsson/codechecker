# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Helper and converter functions for plain text format. """

import logging
import math
import os
import sys

from collections import defaultdict
from typing import Dict, List, Optional, Set

from codechecker_report_converter.report import BugPathEvent, \
    InvalidFileContentMsg, MacroExpansion, Report


LOG = logging.getLogger('report-converter')


def __get_source_file_for_analyzer_result_file(
    analyzer_result_file_path: str,
    metadata: Optional[Dict]
) -> Optional[str]:
    """ Get source file for the given analyzer result file. """
    if not metadata:
        return None

    result_source_files = {}
    if 'result_source_files' in metadata:
        result_source_files = metadata['result_source_files']
    else:
        for tool in metadata.get('tools', {}):
            result_src_files = tool.get('result_source_files', {})
            result_source_files.update(result_src_files.items())

    if analyzer_result_file_path in result_source_files:
        return result_source_files[analyzer_result_file_path]

    return None


def format_main_report(report: Report) -> str:
    """ Format bug path event. """
    line = report.source_line
    if line == '':
        return ''

    marker_line = line[0:(report.column - 1)]
    marker_line = ' ' * (len(marker_line) + marker_line.count('\t'))

    line = line.replace('\t', '  ')

    return f"{line}{marker_line}^"


def format_report(report: Report, content_is_not_changed: bool) -> str:
    """ Format main report. """
    file_path = report.bug_path_events[-1].file.path
    out = f"[{report.severity}] {file_path}:{report.line}:{report.column}: " \
          f"{report.message} [{report.checker_name}]"

    if content_is_not_changed and report.source_code_comments:
        out += f" [{report.review_status.capitalize()}]"

    return out


def format_note(note: BugPathEvent) -> str:
    """ Format bug path note. """
    file_name = os.path.basename(note.file.path)
    return f"{file_name}:{note.line}:{note.column}: {note.message}"


def format_macro_expansion(macro: MacroExpansion) -> str:
    """ Format macro expansions. """
    file_name = os.path.basename(macro.file.path)
    return f"{file_name}:{macro.line}:{macro.column}: Macro '{macro.name}' " \
           f"expanded to '{macro.message}'"


def format_event(event: BugPathEvent) -> str:
    """ Format bug path event. """
    file_name = os.path.basename(event.file.path)
    return f"{file_name}:{event.line}:{event.column}: {event.message}"


def get_index_format(lst: List) -> str:
    """ Get index format. """
    return f'    %{int(math.floor(math.log10(len(lst))) + 1)}d, '


def print_details(report: Report, output=sys.stdout):
    """ Print detail information from the given report. """
    output.write(f'  Report hash: {report.report_hash}\n')

    # Print out macros.
    if report.macro_expansions:
        output.write('  Macro expansions:\n')
        index_format = get_index_format(report.macro_expansions)
        for index, macro in enumerate(report.macro_expansions):
            output.write(index_format % (index + 1))
            output.write(f"{format_macro_expansion(macro)}\n")

    # Print out notes.
    if report.notes:
        output.write('  Notes:\n')
        index_format = get_index_format(report.notes)
        for index, note in enumerate(report.notes):
            output.write(index_format % (index + 1))
            output.write(f"{format_note(note)}\n")

    # Print out bug path events.
    output.write('  Steps:\n')
    index_format = get_index_format(report.bug_path_events)
    for index, event in enumerate(report.bug_path_events):
        output.write(index_format % (index + 1))
        output.write(f"{format_event(event)}\n")


def get_file_report_map(
    reports: List[Report],
    input_file_path: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, List[Report]]:
    """ Get file report map. """
    file_report_map = defaultdict(list)
    for report in reports:
        file_report_map[report.file.path].append(report)

    if input_file_path:
        source_file = __get_source_file_for_analyzer_result_file(
            input_file_path, metadata)

        # Add source file to the map if it doesn't exists.
        if source_file:
            file_report_map[source_file]

    return file_report_map


def convert(
    source_file_report_map: Dict[str, List[Report]],
    processed_file_paths: Optional[Set[str]] = None,
    print_steps: bool = False,
    output=sys.stdout
):
    """ Convert reports to plain text format. """
    if processed_file_paths is None:
        processed_file_paths = set()

    for file_path in sorted(source_file_report_map, key=str.casefold):
        num_of_active_reports = 0
        reports = sorted(source_file_report_map[file_path],
                         key=lambda report: report.line)
        for report in reports:
            # If file content is changed, do not print the source code comments
            # (if available) and instead of the source line, print a warning
            # message.
            content_is_not_changed = \
                report.file.original_path not in report.changed_files

            if content_is_not_changed:
                report.dump_source_code_comment_warnings()

            output.write(f"{format_report(report, content_is_not_changed)}\n")

            if content_is_not_changed:
                # Print source code comments.
                for source_code_comment in report.source_code_comments:
                    if source_code_comment.line:
                        output.write(f"{source_code_comment.line.rstrip()}\n")

                output.write(f"{format_main_report(report)}")
            else:
                output.write(InvalidFileContentMsg)

            output.write("\n")

            if print_steps:
                print_details(report)

            output.write("\n")
            output.flush()

            num_of_active_reports += 1

        file_name = os.path.basename(file_path)
        if num_of_active_reports:
            output.write(f"Found {num_of_active_reports} defect(s) in "
                         f"{file_name}\n\n")
        elif file_path not in processed_file_paths:
            output.write(f"Found no defects in {file_name}\n")

        processed_file_paths.add(file_path)
