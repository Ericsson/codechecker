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
import sys
import fnmatch
import re

from typing import Dict, List, Optional, TextIO


LOG = logging.getLogger('report-converter')


def get_last_mod_time(file_path: str) -> Optional[float]:
    """ Return the last modification time of a file. """
    try:
        return os.stat(file_path).st_mtime
    except OSError as err:
        LOG.debug("File is missing: %s", err)
        return None


def get_linef(fp: TextIO, line_no: int) -> str:
    """'fp' should be (readable) file object.
    Return the line content at line_no or an empty line
    if there is less lines than line_no.
    """
    fp.seek(0)
    for line in fp:
        line_no -= 1
        if line_no == 0:
            return line
    return ''


def get_line(file_path: str, line_no: int, errors: str = 'ignore') -> str:
    """
    Return the given line from the file. If line_no is larger than the number
    of lines in the file then empty string returns.
    If the file can't be opened for read, the function also returns empty
    string.

    Try to encode every file as utf-8 to read the line content do not depend
    on the platform settings. By default locale.getpreferredencoding() is used
    which depends on the platform.

    Changing the encoding error handling can influence the hash content!
    """
    try:
        with open(file_path, mode='r', encoding='utf-8', errors=errors) as f:
            return get_linef(f, line_no)
    except IOError:
        LOG.warning("Failed to open file %s", file_path)
        return ''


def trim_path_prefixes(path: str, prefixes: Optional[List[str]]) -> str:
    """
    Removes the longest matching leading path from the file path.
    """

    # If no prefixes are specified.
    if not prefixes:
        return path

    # Find the longest matching prefix in the path.
    longest_matching_prefix = None
    for prefix in prefixes:
        if not prefix.endswith('/'):
            prefix += '/'

        regex_str = fnmatch.translate(prefix)
        assert regex_str[-2:] == '\\Z', \
               r'fnmatch.translate should leave \\Z at the end of the matcher!'

        prefix_matcher = re.compile(regex_str[:-2])

        matches = prefix_matcher.match(path)
        if matches:
            matching_prefix = matches[0]
            if not longest_matching_prefix or \
                    len(longest_matching_prefix) < len(matching_prefix):

                longest_matching_prefix = matching_prefix

    # If no prefix found or the longest prefix is the root do not trim the
    # path.
    if not longest_matching_prefix or longest_matching_prefix == '/':
        return path

    return path[len(longest_matching_prefix):]


def dump_json_output(
    data: Dict,
    output_file_path: Optional[str] = None,
    out=sys.stdout
) -> str:
    """
    Write JSON data to the given output file and returns the written output.
    """
    data_str = json.dumps(data)

    # Write output data to the file if given.
    if output_file_path:
        with open(output_file_path, mode='w',
                  encoding='utf-8', errors="ignore") as f:
            f.write(data_str)

        LOG.info('JSON report file was created: %s', output_file_path)
    elif out:
        out.write(f"{data_str}\n")

    return data_str
