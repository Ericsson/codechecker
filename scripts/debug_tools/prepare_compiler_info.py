#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
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
        new_json_data[compiler] = dict()
        for language in json_data[compiler]:
            lines = json_data[compiler][language]['compiler_includes']
            changed_lines = []
            for line in lines:
                changed_lines.append(lib.change_paths(
                    line, lib.IncludePathModifier(sources_root_abs)))
            new_json_data[compiler][language] = {
                'compiler_includes': changed_lines,
                'target': json_data[compiler][language]['target'],
                'compiler_standard':
                    json_data[compiler][language]['compiler_standard']
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
