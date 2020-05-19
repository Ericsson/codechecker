# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Parsers for the analyzer output formats (plist ...) should create this
Report which will be stored.

Multiple bug identification hash-es can be generated.
All hash generation algorithms should be documented and implemented here.
"""


import hashlib
import logging
import os

LOG = logging.getLogger('ReportConverter')


def get_line(file_name, line_no, errors='ignore'):
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
        with open(file_name, mode='r',
                  encoding='utf-8',
                  errors=errors) as source_file:
            for line in source_file:
                line_no -= 1
                if line_no == 0:
                    return line
            return ''
    except IOError:
        LOG.error("Failed to open file %s", file_name)
        return ''


def remove_whitespace(line_content, old_col):
    """ Removes white spaces from the given line content.

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


def generate_report_hash(main_section, source_file):
    """ Generate unique hashes for reports.

    Hash generation algoritm for older plist versions where no issue hash was
    generated or for the plists generated where the issue hash generation
    feature is still missing.

    High level overview of the hash content:
     * file_name from the main diag section
     * checker message
     * line content from the source file if can be read up
     * column numbers from the main diag sections location
     * all the whitespaces from the source content are removed

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
