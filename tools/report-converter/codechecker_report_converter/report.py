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

import logging


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
