# -*- coding: utf-8 -*-
#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import argparse
import os
import re

COMMENT_BEGIN = '/* Unicode comment\n'
COMMENT_END = '\nUnicode comment */'

COMMENT = \
    r"""Hungarian special characters:
áÁ éÉ íÍ óÓ öÖ őŐ úÚ üÜ űŰ

Other special characters:
äÄ åÅ àÀ âÂ æÆ çÇ èÈ êÊ ëË îÎ ïÏ ôÔ œŒ ß ùÙ ûÛ ÿŸ"""

# Somebody might have written into the line directly after the comment,
# if so do not remove '\n'
COMMENT_PATTERN = re.compile(
    r'\n' + re.escape(COMMENT_BEGIN) + r'.*?' + re.escape(
        COMMENT_END) + r'(\n(?=\n|$))?', re.DOTALL)


def add_comment_to_file(args, file_path):
    if args.remove:
        print('Removing comments from %s' % file_path)
        full_comment = ''
    else:
        print('Adding the comment to %s' % file_path)
        full_comment = '\n' + COMMENT_BEGIN + COMMENT + COMMENT_END + '\n'

    with open(file_path, 'r+', encoding="utf-8", errors="ignore") as handle:
        text = handle.read()
        text = re.sub(COMMENT_PATTERN, '', text)
        text += full_comment

        handle.seek(0)
        handle.truncate()
        handle.write(text)


def add_comment_to_directory(args, dir_path):
    for root, _, files in os.walk(dir_path):
        for file_name in files:
            if not re.match(r'.*(\.c|\.h|\.cpp|\.hpp|\.cxx|\.hxx)$',
                            file_name):
                continue
            file_path = os.path.join(root, file_name)
            add_comment_to_file(args, file_path)


def main():
    parser = argparse.ArgumentParser(
        description="This script appends a C block comment containing "
                    "special Unicode characters to the end of the source "
                    "files.")

    parser.add_argument('--remove', '-r',
                        action='store_true',
                        dest='remove',
                        help='Remove the comments from the files.')

    parser.add_argument(dest='paths',
                        nargs='*',
                        help="The paths of the source files or the "
                             "directories containing the source files. "
                             "Directories are explored recursively.")

    args = parser.parse_args()

    if args.paths:
        for path in args.path:
            full_path = os.path.realpath(path)
            if os.path.isfile(full_path):
                add_comment_to_file(args, full_path)
            elif os.path.isdir(full_path):
                add_comment_to_directory(args, full_path)
            else:
                print('%s is not a valid file or directory.' % path)
    else:
        add_comment_to_directory(args, os.getcwd())


if __name__ == '__main__':
    main()
