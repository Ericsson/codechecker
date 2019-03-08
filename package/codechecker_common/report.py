# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parsers for the analyzer output formats (plist ...) should create this
Report which will be stored.

Multiple bug identification hash-es can be generated.
All hash generation algorithms should be documented and implemented here.

"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import hashlib
import json
import os
import plistlib
import sys
import traceback
from xml.parsers.expat import ExpatError

from codechecker_common.logger import get_logger
from codechecker_common.util import get_line

LOG = get_logger('report')


def generate_report_hash(path, source_file, check_name):
    """
    !!! Compatible with the old hash before v6.0

    Keep this until needed for transformation tools from the old
    hash to the new hash.

    Hash generation algoritm for older plist versions where no
    issue hash was generated or for the plists generated
    from clang-tidy where the issue hash generation feature
    is still missing.

    As the main diagnositc section the last element from the
    bug path is used.

    High level overview of the hash content:
     * file_name from the main diag section.
     * checker name
     * checker message
     * line content from the source file if can be read up
     * column numbers from the main diag section
     * range column numbers only from the control diag sections if
       column number in the range is not the same as the previous
       control diag section number in the bug path. If there are no control
       sections event section column numbers are used.

    """

    def compare_ctrl_sections(curr, prev):
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

    # The last diag section from the bug path used as a main
    # diagnostic section.
    try:
        ctrl_sections = [x for x in path if x.get('kind') == 'control']

        main_section = path[-1]

        m_loc = main_section.get('location')
        source_line = m_loc.get('line')

        from_col = m_loc.get('col')
        until_col = m_loc.get('col')

        # WARNING!!! Changing the error handling type for encoding errors
        # can influence the hash content!
        line_content = get_line(source_file, source_line, errors='ignore')

        if line_content == '' and not os.path.isfile(source_file):
            LOG.error("Failed to generate report hash.")
            LOG.error('%s does not exists!', source_file)

        file_name = os.path.basename(source_file)
        msg = main_section.get('message')

        hash_content = [file_name,
                        check_name,
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

        string_to_hash = '|||'.join(hash_content)
        return hashlib.md5(string_to_hash.encode()).hexdigest()

    except Exception as ex:
        LOG.error("Hash generation failed")
        LOG.error(ex)
        return ''


def remove_whitespace(line_content, old_col):
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
    content_begin_strip = u''.join(content_begin.split())
    line_strip_len = len(content_begin) - len(content_begin_strip)

    return ''.join(line_content.split()), \
           old_col - line_strip_len


def generate_report_hash_no_bugpath(main_section, source_file):
    """
    !!! NOT Compatible with the old hash generation method

    High level overview of the hash content:
     * file_name from the main diag section
     * checker message
     * line content from the source file if can be read up
     * column numbers from the main diag sections location
     * whitespaces from the beginning of the source content are removed

    """

    try:
        m_loc = main_section.get('location')
        source_line = m_loc.get('line')

        from_col = m_loc.get('col')
        until_col = m_loc.get('col')

        # WARNING!!! Changing the error handling type for encoding errors
        # can influence the hash content!
        line_content = get_line(source_file, source_line, errors='ignore')

        # Remove whitespaces so the hash will be independet of the
        # source code indentation.
        line_content, new_col = \
            remove_whitespace(line_content, from_col)
        # Update the column number in sync with the
        # removed whitespaces.
        until_col = until_col - (from_col-new_col)
        from_col = new_col

        if line_content == '' and not os.path.isfile(source_file):
            LOG.error("Failed to include soruce line in the report hash.")
            LOG.error('%s does not exists!', source_file)

        file_name = os.path.basename(source_file)
        msg = main_section.get('description')

        hash_content = [file_name,
                        msg,
                        line_content,
                        str(from_col),
                        str(until_col)]

        string_to_hash = '|||'.join(hash_content)
        return hashlib.md5(string_to_hash.encode()).hexdigest()

    except Exception as ex:
        LOG.error("Hash generation failed")
        LOG.error(ex)
        return ''


def get_report_path_hash(report, files):
    """
    Returns path hash for the given report. This can be used to filter
    deduplications of multiple reports.
    """
    report_path_hash = ''
    events = filter(lambda i: i.get('kind') == 'event', report.bug_path)

    for event in events:
        file_name = os.path.basename(files[event['location']['file']])
        line = str(event['location']['line']) if 'location' in event else 0
        col = str(event['location']['col']) if 'location' in event else 0

        report_path_hash += line + '|' + col + '|' + event['message'] + \
            file_name

    if not report_path_hash:
        LOG.error('Failed to generate report path hash!')
        LOG.error(report)
        LOG.error(events)

    LOG.debug(report_path_hash)
    return hashlib.md5(report_path_hash.encode()).hexdigest()


class Report(object):
    """
    Just a minimal separation of the main section
    from the path section for easier skip/suppression handling
    and result processing.
    """
    def __init__(self, main, bugpath, files):
        # Dictionary containing checker name, report hash,
        # main report position, report message ...
        self.__main = main

        # Dictionary containing bug path related data
        # with control, event ... sections.
        self.__bug_path = bugpath

        # Dictionary fileid to filepath that bugpath events refer to
        self.__files = files

    @property
    def main(self):
        return self.__main

    @property
    def report_hash(self):
        return self.__main['issue_hash_content_of_line_in_context']

    @property
    def bug_path(self):
        return self.__bug_path

    @property
    def notes(self):
        return self.__main.get('notes', [])

    @property
    def macro_expansions(self):
        return self.__main.get('macro_expansions', [])

    @property
    def files(self):
        return self.__files

    @property
    def file_path(self):
        return self.__files[self.__main['location']['file']]

    def __str__(self):
        msg = json.dumps(self.__main, sort_keys=True, indent=2)
        msg += str(self.__files)
        return msg


def use_context_free_hashes(path):
    """
    Override issue hash in the given file by using context free hashes.
    """
    try:
        plist = plistlib.readPlist(path)

        files = plist['files']

        for diag in plist['diagnostics']:
            file_path = files[diag['location']['file']]

            report_hash = generate_report_hash_no_bugpath(diag, file_path)
            diag['issue_hash_content_of_line_in_context'] = report_hash

        if plist['diagnostics']:
            plistlib.writePlist(plist, path)

    except (ExpatError, TypeError, AttributeError) as err:
        LOG.warning('Failed to process plist file: %s wrong file format?',
                    path)
        LOG.warning(err)
    except IndexError as iex:
        LOG.warning('Indexing error during processing plist file %s', path)
        LOG.warning(type(iex))
        LOG.warning(repr(iex))
        _, _, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    except Exception as ex:
        LOG.warning('Error during processing reports from the plist file: %s',
                    path)
        traceback.print_exc()
        LOG.warning(type(ex))
        LOG.warning(ex)
