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
import plistlib
import sys
import traceback

from enum import Enum

from typing import List, Optional, Tuple

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from mypy_extensions import TypedDict

LOG = logging.getLogger('codechecker_report_hash')

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] - %(message)s')
handler.setFormatter(formatter)

LOG.setLevel(logging.INFO)
LOG.addHandler(handler)


class DiagLoc(TypedDict):
    line: int
    col: int


class DiagEdge(TypedDict):
    start: Tuple[DiagLoc, DiagLoc]
    end: Tuple[DiagLoc, DiagLoc]


class DiagPath(TypedDict):
    kind: str
    message: str
    location: DiagLoc
    edges: List[DiagEdge]


class Diag(TypedDict):
    description: str
    check_name: str
    location: DiagLoc
    path: List[DiagPath]


class HashType(Enum):
    """ Report hash types. """
    CONTEXT_FREE = 1
    PATH_SENSITIVE = 2
    DIAGNOSTIC_MESSAGE = 3


def __get_line(file_path: str, line_no: int, errors: str = 'ignore') -> str:
    """ Return the given line from the file.

    If line_no is larger than the number of lines in the file then empty
    string returns. If the file can't be opened for read, the function also
    returns empty string.

    Try to encode every file as utf-8 to read the line content do not depend
    on the platform settings. By default locale.getpreferredencoding() is used
    which depends on the platform.

    Changing the encoding error handling can influence the hash content!
    """
    try:
        with open(file_path, mode='r',
                  encoding='utf-8', errors=errors) as f:
            for line in f:
                line_no -= 1
                if line_no == 0:
                    return line
            return ''
    except IOError:
        LOG.error("Failed to open file %s", file_path)
        return ''


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


def __get_report_hash_path_sensitive(diag: Diag, file_path: str) -> List[str]:
    """ Report hash generation from the given diagnostic.

    Hash generation algorithm for older plist versions where no
    issue hash was generated or for the plists generated
    from Clang Tidy where the issue hash generation feature
    is still missing.

    As the main diagnostic section the last element from the bug path is used.

    High level overview of the hash content:
     * 'file_name' from the main diag section.
     * 'checker name'
     * 'checker message'
     * 'line content' from the source file if can be read up
     * 'column numbers' from the main diag section
     * 'range column numbers' only from the control diag sections if
       column number in the range is not the same as the previous
       control diag section number in the bug path. If there are no control
       sections event section column numbers are used.
    """
    def compare_ctrl_sections(
        curr: DiagPath,
        prev: DiagPath
    ) -> Optional[Tuple[int, int]]:
        """
        Compare two sections and return column numbers which
        should be included in the path hash or None if the
        two compared sections ranges are identical.
        """
        curr_edges = curr['edges']
        curr_start_range_begin = curr_edges[0]['start'][0]
        curr_start_range_end = curr_edges[0]['start'][1]

        prev_edges = prev['edges']
        prev_end_range_begin = prev_edges[0]['end'][0]
        prev_end_range_end = prev_edges[0]['end'][1]

        if curr_start_range_begin != prev_end_range_begin and \
                curr_start_range_end != prev_end_range_end:
            return (curr_start_range_begin['col'],
                    curr_start_range_end['col'])

        return None

    path = diag['path']

    # The last diag section from the bug path used as a main
    # diagnostic section.
    try:
        ctrl_sections = [x for x in path if x.get('kind') == 'control']

        main_section = path[-1]

        m_loc = main_section.get('location', {})
        source_line = m_loc.get('line', -1)

        from_col = m_loc.get('col', -1)
        until_col = m_loc.get('col', -1)

        # WARNING!!! Changing the error handling type for encoding errors
        # can influence the hash content!
        line_content = __get_line(file_path, source_line, errors='ignore')

        if line_content == '' and not os.path.isfile(file_path):
            LOG.error("Failed to generate report hash.")
            LOG.error('%s does not exists!', file_path)

        file_name = os.path.basename(file_path)
        msg = main_section.get('message', '')

        hash_content = [file_name,
                        diag.get('check_name', 'unknown'),
                        msg,
                        line_content,
                        str(from_col),
                        str(until_col)]

        hash_from_ctrl_section = True
        for i, section in enumerate(ctrl_sections):
            edges = section['edges']

            try:
                start_range_begin = edges[0]['start'][0]
                start_range_end = edges[0]['start'][1]

                end_range_begin = edges[0]['end'][0]
                end_range_end = edges[0]['end'][1]

                if i > 0:
                    prev = ctrl_sections[i-1]
                    col_to_append = compare_ctrl_sections(section, prev)
                    if col_to_append:
                        begin_col, end_col = col_to_append
                        hash_content.append(str(begin_col))
                        hash_content.append(str(end_col))
                else:
                    hash_content.append(str(start_range_begin['col']))
                    hash_content.append(str(start_range_end['col']))

                hash_content.append(str(end_range_begin['col']))
                hash_content.append(str(end_range_end['col']))
            except IndexError:
                # Edges might be empty.
                hash_from_ctrl_section = False

        # Hash generation from the control sections failed for some reason
        # use event section positions for hash generation.
        if not hash_from_ctrl_section:
            event_sections = [x for x in path if x.get('kind') == 'event']

            for i, section in enumerate(event_sections):
                loc = section['location']
                col_num = loc['col']
                hash_content.append(str(col_num))

        return hash_content
    except Exception as ex:
        LOG.error("Hash generation failed")
        LOG.error(ex)
        return []


def __get_report_hash_context_free(diag: Diag, file_path: str) -> List[str]:
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
        m_loc = diag.get('location', {})
        source_line = m_loc.get('line', -1)

        from_col = m_loc.get('col', -1)
        until_col = m_loc.get('col', -1)

        # WARNING!!! Changing the error handling type for encoding errors
        # can influence the hash content!
        line_content = __get_line(file_path, source_line, errors='ignore')

        # Remove whitespaces so the hash will be independet of the
        # source code indentation.
        line_content, new_col = _remove_whitespace(line_content, from_col)

        # Update the column number in sync with the
        # removed whitespaces.
        until_col = until_col - (from_col - new_col)
        from_col = new_col

        if line_content == '' and not os.path.isfile(file_path):
            LOG.error("Failed to include soruce line in the report hash.")
            LOG.error('%s does not exists!', file_path)

        file_name = os.path.basename(file_path)
        msg = diag.get('description', '')

        hash_content = [file_name,
                        msg,
                        line_content,
                        str(from_col),
                        str(until_col)]

        return hash_content
    except Exception as ex:
        LOG.error("Hash generation failed")
        LOG.error(ex)
        return []


def __get_report_hash_diagnostic_message(
    diag: Diag,
    file_path: str
) -> List[str]:
    """ Generate report hash with bug path messages.

    The hash will contain the same information as the CONTEXT_FREE hash +
    'bug step messages' from events.
    """
    try:
        hash_content = __get_report_hash_context_free(diag, file_path)

        # Add bug step messages to the hash.
        for event in [x for x in diag['path'] if x.get('kind') == 'event']:
            hash_content.append(event['message'])

        return hash_content
    except Exception as ex:
        LOG.error("Hash generation failed")
        LOG.error(ex)
        return []


def get_report_hash(diag: Diag, file_path: str, hash_type: HashType) -> str:
    """ Get report hash for the given diagnostic. """
    hash_content = None

    if hash_type == HashType.CONTEXT_FREE:
        hash_content = __get_report_hash_context_free(diag, file_path)
    elif hash_type == HashType.PATH_SENSITIVE:
        hash_content = __get_report_hash_path_sensitive(diag, file_path)
    elif hash_type == HashType.DIAGNOSTIC_MESSAGE:
        hash_content = __get_report_hash_diagnostic_message(diag, file_path)
    else:
        raise Exception("Invalid report hash type: " + str(hash_type))

    return __str_to_hash('|||'.join(hash_content))


def get_report_path_hash(report) -> str:
    """ Returns path hash for the given bug path.

    This can be used to filter deduplications of multiple reports.

    report type should be codechecker_common.Report
    """
    report_path_hash = ''
    events = [i for i in report.bug_path if i.get('kind') == 'event']
    for event in events:
        file_name = \
            os.path.basename(report.files.get(event['location']['file']))
        line = str(event['location']['line'] if 'location' in event else 0)
        col = str(event['location']['col'] if 'location' in event else 0)

        report_path_hash += line + '|' + col + '|' + event['message'] + \
            file_name

    report_path_hash += report.check_name

    if not report_path_hash:
        LOG.error('Failed to generate report path hash!')
        LOG.error(report.bug_path)

    LOG.debug(report_path_hash)
    return __str_to_hash(report_path_hash)


def replace_report_hash(plist_file: str, hash_type=HashType.CONTEXT_FREE):
    """ Override hash in the given file by using the given version hash. """
    try:
        with open(plist_file, 'rb+') as f:
            plist = plistlib.load(f)
            f.seek(0)
            f.truncate()
            files = plist['files']

            for diag in plist['diagnostics']:
                file_path = files[diag['location']['file']]
                report_hash = get_report_hash(diag, file_path, hash_type)
                diag['issue_hash_content_of_line_in_context'] = report_hash

            plistlib.dump(plist, f)

    except (TypeError, AttributeError, plistlib.InvalidFileException) as err:
        LOG.warning('Failed to process plist file: %s wrong file format?',
                    plist_file)
        LOG.warning(err)
    except IndexError as iex:
        LOG.warning('Indexing error during processing plist file %s',
                    plist_file)
        LOG.warning(type(iex))
        LOG.warning(repr(iex))
        _, _, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    except Exception as ex:
        LOG.warning('Error during processing reports from the plist file: %s',
                    plist_file)
        traceback.print_exc()
        LOG.warning(type(ex))
        LOG.warning(ex)
