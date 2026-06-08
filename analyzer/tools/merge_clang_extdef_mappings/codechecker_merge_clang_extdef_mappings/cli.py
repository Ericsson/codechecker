#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import argparse
import logging
import os
import sys

# If we run this script in an environment where
# 'codechecker_merge_clang_extdef_mappings' module is not available we should
# add the grandparent directory of this file to the system path.
# TODO: This section will not be needed when CodeChecker will be delivered as
# a python package and will be installed in a virtual environment with all the
# dependencies.
if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.realpath(__file__))
    os.sys.path.append(os.path.dirname(current_dir))

from codechecker_merge_clang_extdef_mappings import \
    merge_clang_extdef_mappings  # noqa


LOG = logging.getLogger('MergeClangExtdefMappings')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


def __add_arguments_to_parser(parser):
    """ Add arguments to the the given parser. """
    parser.add_argument('-i', '--input',
                        type=str,
                        metavar='input',
                        required=True,
                        help="Folder which contains multiple output of the "
                             "'clang-extdef-mapping' tool.")

    parser.add_argument('-o', '--output',
                        type=str,
                        metavar='output',
                        required=True,
                        help="Output file where the merged function maps will "
                             "be stored into.")


def main():
    """ Merge CTU funcs maps main command line. """
    parser = argparse.ArgumentParser(
        prog="merge-clang-extdef-mappings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Merge individual clang extdef mapping files into one "
                    "mapping file.",
        epilog="""Example:
  merge-clang-extdef-mappings -i /path/to/fn_map_folder
  /path/to/externalDefMap.txt""")

    __add_arguments_to_parser(parser)

    args = parser.parse_args()

    merge_clang_extdef_mappings.merge(args.input, args.output)


if __name__ == "__main__":
    main()
