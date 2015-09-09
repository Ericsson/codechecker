# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
''' suppress file format

123324353456463442341242342343#1 || bug hash comment
/sdfsfs/sdf/ || some path to suppress

'''

import os
import string
import codecs
from codechecker_lib import logger

LOG = logger.get_new_logger('SUPPRESS_FILE_HANDLER')


COMMENT_SEPARATOR = '||'
HASH_TYPE_SEPARATOR = '#'


def get_hash_and_path(suppress_file):

    paths, hashes = {}, {}

    def is_bug_hash(line):
        valid_chars = string.hexdigits + HASH_TYPE_SEPARATOR
        return all(c in valid_chars for c in line) and len(line) == 34

    LOG.debug('Processing suppress file: '+suppress_file)

    if os.path.exists(suppress_file):
        with codecs.open(suppress_file, 'r', 'UTF-8') as s_file:
            for line in s_file:
                if line == '':
                    # skip empty lines
                    continue
                res = line.split(COMMENT_SEPARATOR)
                if len(res) == 2:
                    # there is a comment

                    data = res[0].strip()
                    comment = res[1].strip()
                    if is_bug_hash(data):
                        hashes[data] = comment
                    else:
                        paths[data] = comment
                if len(res) == 1:
                    data = res[0].strip()
                    if is_bug_hash(data):
                        hashes[data] = ''
                    else:
                        paths[data] = ''

    LOG.debug(hashes)
    LOG.debug(paths)

    return hashes, paths


# ---------------------------------------------------------------------------
def write_to_suppress_file(supp_file, value, hash_type, comment=''):

    comment = comment.decode('UTF-8')

    hashes, paths = get_hash_and_path(supp_file)

    value = value+HASH_TYPE_SEPARATOR+str(hash_type)
    try:
        if not os.stat(supp_file)[6] == 0:
            if value in hashes or value in paths:
                LOG.debug("Already found in\n %s" % (supp_file))
                return True

        s_file = codecs.open(supp_file, 'a', 'UTF-8')

        s_file.write(value+COMMENT_SEPARATOR+comment+'\n')
        s_file.close()

        return True

    except Exception as ex:
        LOG.error(str(ex))
        LOG.error("Failed to write: %s" % (supp_file))
        return False


def remove_from_suppress_file(supp_file, value, hash_type):

    LOG.debug('Removing ' + value + ' from \n' + supp_file)

    try:
        s_file = codecs.open(supp_file, 'r+', 'UTF-8')
        lines = s_file.readlines()

        lines = filter(lambda line: not line.startswith(value +
                                                        HASH_TYPE_SEPARATOR +
                                                        str(hash_type) +
                                                        COMMENT_SEPARATOR),
                       lines)

        s_file.seek(0)
        s_file.truncate()
        s_file.writelines(lines)
        s_file.close()

        return True

    except Exception as ex:
        LOG.error(str(ex))
        LOG.error("Failed to write: %s" % (supp_file))
        return False
