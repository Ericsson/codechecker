# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""" This file contains some workaround for CodeChecker
to work with older clang versions. It is for demonstration purposes only.
The names, hashes will change after switching to a newer clang version.
"""

import hashlib
import linecache
import json
import os
import re

from codechecker_lib.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('PLIST_HELPER')


def gen_bug_hash(bug):
    line_content = linecache.getline(bug.file_path, bug.from_line)
    if line_content == '' and not os.path.isfile(bug.file_path):
        LOG.debug('%s does not exists!' % bug.file_path)

    file_name = os.path.basename(bug.file_path)
    l = [file_name, bug.checker_name, bug.msg, line_content,
         str(bug.from_col), str(bug.until_col)]
    for p in bug.paths():
        l.append(str(p.start_pos.col))
        l.append(str(p.end_pos.col))
    string_to_hash = '|||'.join(l)
    return hashlib.md5(string_to_hash.encode()).hexdigest()


def levenshtein(a, b):  # http://hetland.org/coding/python/levenshtein.py
    """"Calculates the Levenshtein distance between a and b."""
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space.
        a, b = b, a
        n, m = m, n

    current = range(n+1)
    for i in range(1, m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1, n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)

    return current[n]


def get_check_name(current_msg):
    # Clean message from variable and class name.
    clean_msg = re.sub(r"'.*?'", '', current_msg)

    closest_msg = ''
    min_dist = len(clean_msg) // 4

    message_map_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'checker_message_map.json')

    checker_message_map = {}
    with open(message_map_path) as map_file:
        checker_message_map = json.load(map_file)

    for msg in checker_message_map.keys():
        tmp_dist = levenshtein(clean_msg, msg)
        if tmp_dist < min_dist:
            closest_msg = msg
            min_dist = tmp_dist

    return checker_message_map[closest_msg]
