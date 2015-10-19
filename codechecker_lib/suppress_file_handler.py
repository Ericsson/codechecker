# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
''' suppress file format

# this is the old format
123324353456463442341242342343#1 || bug hash comment

# this is the new format
123324353456463442341242342343#1 || filename || bug hash comment

'''

import re
import os
import string
import codecs
from codechecker_lib import logger

LOG = logger.get_new_logger('SUPPRESS_FILE_HANDLER')


COMMENT_SEPARATOR = '||'
HASH_TYPE_SEPARATOR = '#'


def get_suppress_data(suppress_file):
    """
    processs a file object for suppress information
    """

    old_format_pattern = r"^(?P<bug_hash>[\d\w]{32})\#(?P<bug_hash_type>\d)\s*\|\|\s*(?P<comment>[^\|]*)$"
    old_format = re.compile(old_format_pattern, re.UNICODE)

    new_format_pattern = r"^(?P<bug_hash>[\d\w]{32})\#(?P<bug_hash_type>\d)\s*\|\|\s*(?P<file_name>[^\\\|]+)\s*\|\|\s*(?P<comment>[^\|]*)$"
    new_format = re.compile(new_format_pattern, re.UNICODE)

    suppress_data = []

    for line in suppress_file:

        new_format_match = re.match(new_format, line.strip())
        if new_format_match:
            LOG.debug('Match for new suppress entry format:')
            new_format_match = new_format_match.groupdict()
            LOG.debug(new_format_match)
            suppress_data.append((new_format_match['bug_hash'],
                                  new_format_match['bug_hash_type'],
                                  new_format_match['file_name'],
                                  new_format_match['comment']))
            continue

        old_format_match = re.match(old_format, line.strip())
        if old_format_match:
            LOG.debug('Match for old suppress entry format:')
            old_format_match = old_format_match.groupdict()
            LOG.debug(old_format_match)
            suppress_data.append((old_format_match['bug_hash'],
                                  old_format_match['bug_hash_type'],
                                  u'',  # empty file name
                                  old_format_match['comment']))
            continue

        if line.strip() != '':
            LOG.warning('Malformed suppress line: ' + line)

    return suppress_data

# ---------------------------------------------------------------------------
def write_to_suppress_file(suppress_file, value, hash_type, file_name, comment=''):

    comment = comment.decode('UTF-8')

    LOG.debug('Processing suppress file: '+suppress_file)

    if os.path.exists(suppress_file):
        with codecs.open(suppress_file, 'r', 'UTF-8') as s_file:
            suppress_data = get_suppress_data(s_file)

    value = value+HASH_TYPE_SEPARATOR+str(hash_type)
    try:
        if not os.stat(suppress_file)[6] == 0:
            # file is not empty

            res = filter(lambda x: (x[0] == value and x[1] == file_name) or (x[0] == value and x[1] == ''), suppress_data)

            if res:
                LOG.debug("Already found in\n %s" % (suppress_file))
                return True

        s_file = codecs.open(suppress_file, 'a', 'UTF-8')

        s_file.write(value+COMMENT_SEPARATOR+file_name+COMMENT_SEPARATOR+comment+'\n')
        s_file.close()

        return True

    except Exception as ex:
        LOG.error(str(ex))
        LOG.error("Failed to write: %s" % (suppress_file))
        return False


def remove_from_suppress_file(suppress_file, value, hash_type, file_name):
    """
    remove suppress information from the suppress file
    old and new format is supported
    """

    LOG.debug('Removing ' + value + ' from \n' + suppress_file)

    try:
        s_file = codecs.open(suppress_file, 'r+', 'UTF-8')
        lines = s_file.readlines()

        # filter out new format first because it is more specific
        old_format_pattern = r"^" + value + r"\#" + str(hash_type) + \
            r"\s*\|\|\s*(?P<comment>[^\|]*)$"
        old_format = re.compile(old_format_pattern, re.UNICODE)

        new_format_pattern = r"^" + value + r"\#" + str(hash_type) + \
            r"\s*\|\|\s*" + file_name + r"\s*\|\|\s*(?P<comment>[^\|]*)$"
        new_format = re.compile(new_format_pattern, re.UNICODE)

        def check_for_match(line):
            """
            check if the line matches the new or old format
            """
            line = line.strip()
            if re.match(new_format, line.strip()):
                return False
            if re.match(old_format, line.strip()):
                return False
            else:
                return True

        # filter out lines which should be removed
        lines = filter(lambda line: check_for_match(line), lines)

        s_file.seek(0)
        s_file.truncate()
        s_file.writelines(lines)
        s_file.close()

        return True

    except Exception as ex:
        LOG.error(str(ex))
        LOG.error("Failed to write: %s" % (suppress_file))
        return False
