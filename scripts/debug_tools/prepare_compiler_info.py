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

# Until CodeChecker 6.19.0 it should work.
# On failure, raises an exception.
def _try_prepare_as_old_format(compiler_info_file, sources_root):
    json_data = lib.load_json_file(compiler_info_file)
    sources_root_abs = os.path.abspath(sources_root)
    new_json_data = {}
    for compiler in json_data:
        new_json_data[compiler] = {}
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

# CodeChecker 6.19.0 and above it should parse according to the new format.
# More details: #3598 [analyzer] Proper handling of multi-target build
# On failure, raises an exception.
def _try_prepare_as_new_format(compiler_info_file, sources_root):
    json_data = lib.load_json_file(compiler_info_file)
    sources_root_abs = os.path.abspath(sources_root)
    new_json_data = {}

    for compiler_id_string in json_data:
        new_json_data[compiler_id_string] = {}
        include_paths = json_data[compiler_id_string]['compiler_includes']
        changed_includes = [
            lib.change_paths(p, lib.IncludePathModifier(sources_root_abs))
            for p in include_paths
        ]

        new_json_data[compiler_id_string] = {
            'compiler_includes': changed_includes,
            'target': json_data[compiler_id_string]['target'],
            'compiler_standard':
                json_data[compiler_id_string]['compiler_standard']
        }
    return new_json_data

def prepare(compiler_info_file, sources_root):
    try:
        return _try_prepare_as_new_format(compiler_info_file, sources_root)
    except Exception:
        print(f"Failed to parse {compiler_info_file} in the 'new' "
              f"compiler_info format; falling back to the old format...")
        return _try_prepare_as_old_format(compiler_info_file, sources_root)

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
