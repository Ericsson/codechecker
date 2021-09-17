# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Suppress file format.

# This is the old format.
123324353456463442341242342343#1 || bug hash comment

# This is the new format.
123324353456463442341242342343#1 || filename || bug hash comment

After removing the hash_value_type the generated format is:
123324353456463442341242342343 || filename || bug hash comment

For backward compatibility the hash_value_type is an optional filed.
"""


import codecs
import os
import re

from codechecker_common.logger import get_logger
from codechecker_report_converter.source_code_comment_handler import \
    SourceCodeCommentHandler

LOG = get_logger('system')

COMMENT_SEPARATOR = '||'
HASH_TYPE_SEPARATOR = '#'


def get_suppress_data(suppress_file):
    """
    Process a file object for suppress information.
    """

    old_format_pattern = r"^(?P<bug_hash>[\d\w]{32})" \
        r"(\#(?P<bug_hash_type>\d))?\s*\|\|\s*(?P<comment>[^\|]*)$"
    old_format = re.compile(old_format_pattern, re.UNICODE)

    new_format_pattern = r"^(?P<bug_hash>[\d\w]{32})" \
        r"(\#(?P<bug_hash_type>\d))?\s*\|\|\s*" \
        r"(?P<file_name>[^\\\|]+)\s*\|\|\s*(?P<comment>[^\|]*)$"
    new_format = re.compile(new_format_pattern, re.UNICODE)

    markers = '|'.join(SourceCodeCommentHandler.source_code_comment_markers)
    src_suppress_format_pattern = r"^(?P<bug_hash>[\d\w]{32})" \
        r"(\#(?P<bug_hash_type>\d))?\s*\|\|\s*" \
        r"(?P<file_name>[^\\\|]+)\s*\|\|\s*(?P<comment>[^\|]*)\s*\|\|\s*" \
        r"(?P<status>[" + markers + "]*)$"
    src_suppress_format = re.compile(src_suppress_format_pattern, re.UNICODE)

    suppress_data = []

    for line in suppress_file:

        src_suppress_format_match = re.match(src_suppress_format, line.strip())
        if src_suppress_format_match:
            LOG.debug('Match for source code suppress entry format:')
            src_suppress_format_match = src_suppress_format_match.groupdict()
            LOG.debug(src_suppress_format_match)
            suppress_data.append((src_suppress_format_match['bug_hash'],
                                  src_suppress_format_match['file_name'],
                                  src_suppress_format_match['comment'],
                                  src_suppress_format_match['status']))
            continue

        new_format_match = re.match(new_format, line.strip())
        if new_format_match:
            LOG.debug('Match for new suppress entry format:')
            new_format_match = new_format_match.groupdict()
            LOG.debug(new_format_match)
            suppress_data.append((new_format_match['bug_hash'],
                                  new_format_match['file_name'],
                                  new_format_match['comment'],
                                  'false_positive'))
            continue

        old_format_match = re.match(old_format, line.strip())
        if old_format_match:
            LOG.debug('Match for old suppress entry format:')
            old_format_match = old_format_match.groupdict()
            LOG.debug(old_format_match)
            suppress_data.append((old_format_match['bug_hash'],
                                  '',  # empty file name
                                  old_format_match['comment'],
                                  'false_positive'))
            continue

        if line.strip() != '':
            LOG.warning('Malformed suppress line: %s', line)

    return suppress_data


def write_to_suppress_file(suppress_file, value, file_name, comment='',
                           status='false_positive'):
    comment = comment.decode('utf-8')

    LOG.debug('Processing suppress file: %s', suppress_file)

    try:
        with codecs.open(suppress_file, 'r', 'utf-8') as s_file:
            suppress_data = get_suppress_data(s_file)

        if not os.stat(suppress_file)[6] == 0:
            # File is not empty.

            res = [
                x for x in suppress_data if (
                    x[0] == value and x[1] == file_name) or (
                    x[0] == value and x[1] == '')]

            if res:
                LOG.debug("Already found in\n %s", suppress_file)
                return True

        s_file = codecs.open(suppress_file, 'a', 'utf-8')

        s_file.write(value + COMMENT_SEPARATOR +
                     file_name + COMMENT_SEPARATOR +
                     comment + COMMENT_SEPARATOR +
                     status + '\n')
        s_file.close()

        return True

    except Exception as ex:
        LOG.error(str(ex))
        LOG.error("Failed to write: %s", suppress_file)
        return False
