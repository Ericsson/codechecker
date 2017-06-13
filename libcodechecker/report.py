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
import hashlib
import json
import linecache
import os

from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('REPORT')


def generate_report_hash(path, files, check_name):
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
        else:
            return None

    # The last diag section from the bug path used as a main
    # diagnostic section.
    try:
        ctrl_sections = [x for x in path if x.get('kind') == 'control']

        main_section = path[-1]

        m_loc = main_section.get('location')
        source_file = files[m_loc.get('file')]
        source_line = m_loc.get('line')

        from_col = m_loc.get('col')
        until_col = m_loc.get('col')

        line_content = linecache.getline(source_file, source_line)

        if line_content == '' and not os.path.isfile(source_file):
            LOG.debug("Failed to generate report hash.")
            LOG.debug('%s does not exists!' % source_file)

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


class Report(object):
    """
    Just a minimal separation of the main section
    from the path section for easier skip/suppression handling
    and result processing.
    """
    def __init__(self, main, bugpath):
        # Dictionary containing checker name, report hash,
        # main report position, report message ...
        self.__main = main

        # Dictionary containing bug path related data
        # with control, event ... sections.
        self.__bug_path = bugpath

    @property
    def main(self):
        return self.__main

    @property
    def bug_path(self):
        return self.__bug_path

    def __str__(self):
        msg = json.dumps(self.__main, sort_keys=True, indent=2)
        return msg
