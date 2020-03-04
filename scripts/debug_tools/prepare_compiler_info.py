#!/usr/bin/env python3
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------


import argparse
import json
import os

import failure_lib as lib


def prepare(compiler_info_file, sources_root):
    json_data = lib.load_json_file(compiler_info_file)
    sources_root_abs = os.path.abspath(sources_root)
    new_json_data = dict()
    for compiler in json_data:
        lines = json_data[compiler]['includes']
        changed_lines = []
        for line in lines:
            changed_lines.append(
                lib.change_paths(line,
                                 lib.IncludePathModifier(sources_root_abs)))
        new_json_data[compiler] = {
            'includes': changed_lines,
            'target': json_data[compiler]['target'],
            'default_standard': json_data[compiler]['default_standard']
        }
    return new_json_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare compiler info '
                                     'json to execute in local environmennt.')
    parser.add_argument('compiler_info_file')
    parser.add_argument('--sources_root', default='./sources-root')
    args = parser.parse_args()

    print(
        json.dumps(
            prepare(
                args.compiler_info_file,
                args.sources_root)))
