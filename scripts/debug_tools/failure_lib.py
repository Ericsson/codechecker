# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Helpers to manage failure zips.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import os
import re
import subprocess


def find_path_end(string, path_begin):
    """
    Find one path in string.
    Returns the pair of the begin and end pos.
    """
    path_end = string.find(' ', path_begin)
    if path_end == -1:
        path_end = len(string)
    path = string[path_begin:path_end]
    return path, path_end


def change_paths(string, pathModifierFun, skip_output=False):
    """
    Scan through the string and possibly replace all found paths.
    Returns the modified string.
    """
    result = []
    i = 0
    while i < len(string):
        # Everything is a path which starts with a '/' and there is a
        # whitespace after that.
        # Note, this supports only POSIX paths.
        if string[i] == '/':
            path, path_end = find_path_end(string, i)
            # Make sure that the prospective output folder exists.
            pattern = re.compile(r'[\s\S]*-o *\Z')
            if pattern.match(string[:i]):
                out_dir = os.path.join("./sources-root",
                                       '.' + os.path.dirname(path))
                if not os.path.isdir(out_dir):
                    os.makedirs(out_dir)
            path = pathModifierFun(path)
            result += path
            i = path_end - 1
        else:
            result.extend(string[i])
        i = i + 1
    return ''.join(result)


class IncludePathModifier(object):
    def __init__(self, sources_root):
        self.sources_root = sources_root

    def __call__(self, path):
        return os.path.join(
            self.sources_root,
            os.path.normpath(
                path.lstrip(
                    os.path.sep)))


def load_json_file(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def get_resource_dir(clang_bin):
    """
    Returns the resource_dir of Clang or None if the switch is not supported by
    Clang.
    """
    cmd = [clang_bin, "-print-resource-dir"]
    try:
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                )
        out, err = proc.communicate()

        if proc.returncode == 0:
            return out.decode("utf-8").rstrip()
        else:
            return None
    except OSError:
        print('Failed to run: "' + ' '.join(cmd) + '"')
        raise
