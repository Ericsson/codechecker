# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" CodeChecker hash generation algorithms. """

import hashlib
import logging
import os

from enum import Enum

from typing import List, Tuple

from codechecker_report_converter.report import Report

LOG = logging.getLogger('report-converter')


class HashType(Enum):
    """ Report hash types. """
    CONTEXT_FREE = 1
    PATH_SENSITIVE = 2
    DIAGNOSTIC_MESSAGE = 3


def __str_to_hash(string_to_hash: str, errors: str = 'ignore') -> str:
    """ Encodes the given string and generates a hash from it. """
    string_hash = string_to_hash.encode(encoding="utf-8", errors=errors)
    return hashlib.md5(string_hash).hexdigest()


def _remove_whitespace(line_content: str, old_col: int) -> Tuple[str, int]:
    """
    This function removes white spaces from the line content parameter and
    calculates the new line location.
    Returns the line content without white spaces and the new column number.
    E.g.:
    line_content = "  int foo = 17;   sizeof(43);  "
                                      ^
                                      |- bug_col = 18
    content_begin = "  int foo = 17;   "
    content_begin_strip = "intfoo=17;"
    line_strip_len = 18 - 10 => 8
    ''.join(line_content.split()) => "intfoo=17;sizeof(43);"
                                                ^
                                                |- until_col - line_strip_len
                                                       18    -     8
                                                             = 10
    """
    content_begin = line_content[:old_col]
    content_begin_strip = ''.join(content_begin.split())
    line_strip_len = len(content_begin) - len(content_begin_strip)

    return ''.join(line_content.split()), \
           old_col - line_strip_len


def __get_report_hash_path_sensitive(report: Report) -> List[str]:
    """ Report hash generation from the given report.

    High level overview of the hash content:
     * 'file_name' from the main diag section.
     * 'checker name'
     * 'checker message'
     * 'line content' from the source file if can be read up
     * 'column numbers' from the main diag section
     * 'range column numbers' from bug_path_positions.
    """
    try:
        event = report.bug_path_events[-1]

        from_col = event.column
        until_col = event.column

        # WARNING!!! Changing the error handling type for encoding errors
        # can influence the hash content!
        line_content = report.file.get_line(event.line)

        if line_content == '' and \
                not os.path.isfile(report.file.original_path):
            LOG.error("Failed to generate report hash. %s does not exists!",
                      report.file.original_path)

        hash_content = [report.file.name,
                        report.checker_name,
                        event.message,
                        line_content,
                        str(from_col),
                        str(until_col)]

        for p in report.bug_path_positions:
            if p.range:
                hash_content.append(str(p.range.start_col))
                hash_content.append(str(p.range.end_col))

        return hash_content
    except Exception as ex:
        LOG.error("Hash generation failed!")
        LOG.error(ex)
        return []


def __get_report_hash_context_free(report: Report) -> List[str]:
    """ Generate report hash without bug path.

    !!! NOT Compatible with the old hash generation method

    High level overview of the hash content:
     * 'file_name' from the main diag section.
     * 'checker message'.
     * 'line content' from the source file if can be read up. All the
       whitespaces from the source content are removed.
     * 'column numbers' from the main diag sections location.
    """
    try:
        from_col = report.column
        until_col = report.column

        # WARNING!!! Changing the error handling type for encoding errors
        # can influence the hash content!
        line_content = report.file.get_line(report.line)

        # Remove whitespaces so the hash will be independet of the
        # source code indentation.
        line_content, new_col = _remove_whitespace(line_content, from_col)

        # Update the column number in sync with the
        # removed whitespaces.
        until_col = until_col - (from_col - new_col)
        from_col = new_col

        if line_content == '' and \
                not os.path.isfile(report.file.original_path):
            LOG.error("Failed to include soruce line in the report hash.")
            LOG.error('%s does not exists!', report.file.original_path)

        return [
            report.file.name,
            report.message,
            line_content,
            str(from_col),
            str(until_col)]
    except Exception as ex:
        LOG.error("Hash generation failed")
        LOG.error(ex)
        return []


def __get_report_hash_diagnostic_message(report: Report) -> List[str]:
    """ Generate report hash with bug path messages.

    The hash will contain the same information as the CONTEXT_FREE hash +
    'bug step messages' from events.
    """
    try:
        hash_content = __get_report_hash_context_free(report)

        # Add bug step messages to the hash.
        for event in report.bug_path_events:
            hash_content.append(event.message)

        return hash_content
    except Exception as ex:
        LOG.error("Hash generation failed: %s", ex)
        return []


def get_report_hash(report: Report, hash_type: HashType) -> str:
    """ Get report hash for the given diagnostic. """
    hash_content = None

    if hash_type == HashType.CONTEXT_FREE:
        hash_content = __get_report_hash_context_free(report)
    elif hash_type == HashType.PATH_SENSITIVE:
        hash_content = __get_report_hash_path_sensitive(report)
    elif hash_type == HashType.DIAGNOSTIC_MESSAGE:
        hash_content = __get_report_hash_diagnostic_message(report)
    else:
        raise Exception("Invalid report hash type: " + str(hash_type))

    return __str_to_hash('|||'.join(hash_content))


def get_report_path_hash(report: Report) -> str:
    """ Returns path hash for the given report.

    This can be used to filter deduplications of multiple reports.
    """
    report_path_hash = ''
    for event in report.bug_path_events:
        line = str(event.line)
        col = str(event.column)
        report_path_hash += f"{line}|{col}|{event.message}|{event.file.path}"

    report_path_hash += report.checker_name
    if report.report_hash:
        report_path_hash += report.report_hash

    if not report_path_hash:
        LOG.error('Failed to generate report path hash: %s', report)

    LOG.debug(report_path_hash)
    return __str_to_hash(report_path_hash)
