#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
import argparse
import json

import failure_lib as lib


def prepare(compiler_target_file, sources_root):
    json_data = lib.load_json_file(compiler_target_file)
    return json_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare compiler target '
                                     'json to execute in local environmennt.')
    parser.add_argument('compiler_target_file')
    parser.add_argument('--sources_root', default='./sources-root')
    args = parser.parse_args()

    print(
        json.dumps(
            prepare(
                args.compiler_target_file,
                args.sources_root)))
