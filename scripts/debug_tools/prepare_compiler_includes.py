#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
import argparse
import json
import os

import failure_lib as lib


def prepare(compiler_includes_file, sources_root):
    json_data = lib.load_json_file(compiler_includes_file)
    new_json_data = dict()
    sources_root_abs = os.path.abspath(sources_root)
    for key, value in json_data.items():
        lines = value.split("\n")
        changed_lines = []
        for line in lines:
            changed_lines.append(
                lib.change_paths(line,
                                 lib.IncludePathModifier(sources_root_abs)))
        new_json_data[key] = "\n".join(changed_lines)
    return new_json_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare compiler includes '
                                     'json to execute in local environmennt.')
    parser.add_argument('compiler_includes_file')
    parser.add_argument('--sources_root', default='./sources-root')
    args = parser.parse_args()

    print(
        json.dumps(
            prepare(
                args.compiler_includes_file,
                args.sources_root)))
