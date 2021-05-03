#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Converts Gerrit Review changed files list to CodeChecker skipfile.
"""

import argparse
import json
import re


def create_skipfile(files_changed, skipfile):
    # File is likely to contain some garbage values at start,
    # only the corresponding json should be parsed.
    json_pattern = re.compile(r"^\{.*\}")
    for line in files_changed.readlines():
        if re.match(json_pattern, line):
            for filename in json.loads(line):
                if "/COMMIT_MSG" in filename:
                    continue
                skipfile.write("+*/%s\n" % filename)

    skipfile.write("-*\n")


def main():
    parser = argparse.ArgumentParser(
        description="Converts Gerrit Review changed files "
        "json to CodeChecker skipfile."
    )
    parser.add_argument(
        "files_changed",
        type=argparse.FileType("r"),
        help="Path of changed files json from Gerrit.",
    )
    parser.add_argument(
        "skipfile",
        nargs="?",
        default="skipfile",
        type=argparse.FileType("w"),
        help="Path of the skipfile output. Default is ./skipfile.",
    )
    args = parser.parse_args()

    create_skipfile(args.files_changed, args.skipfile)


if __name__ == "__main__":
    main()
