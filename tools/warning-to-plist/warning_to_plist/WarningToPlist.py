#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import logging
import os
import sys

from .converter.clang_tidy.plist_converter import ClangTidyPlistConverter

LOG = logging.getLogger('WarningToPlist')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


supported_converters = {
    ClangTidyPlistConverter.TOOL_NAME: ClangTidyPlistConverter}


def output_to_plist(output, parser_type, output_dir):
    """ Creates .plist files from the given output to the given output dir. """
    plist_converter = supported_converters[parser_type]()
    messages = plist_converter.parse_messages(output)

    if not messages:
        LOG.info("No '%s' results can be found in the given code analyzer "
                 "output.", parser_type)
        sys.exit(0)

    converters = {}
    for m in messages:
        if m.path not in converters:
            converters[m.path] = supported_converters[parser_type]()
        converters[m.path].add_messages([m])

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for c in converters:
        file_name = os.path.basename(c)
        out_file_name = '{0}_{1}.plist'.format(file_name, parser_type)
        out_file = os.path.join(output_dir, out_file_name)

        LOG.info("Creating plist file: '%s'.", out_file)
        LOG.debug(converters[c].plist)

        converters[c].write_to_file(out_file)


def __add_arguments_to_parser(parser):
    """ Add arguments to the the given parser. """
    parser.add_argument('input',
                        type=str,
                        metavar='file',
                        nargs='?',
                        default=argparse.SUPPRESS,
                        help="Code analyzer output result file which will be "
                             "parsed and used to generate a CodeChecker "
                             "report directory. If this parameter is not "
                             "given the standard input will be used.")

    parser.add_argument('-o', '--output',
                        dest="output_dir",
                        required=True,
                        default=argparse.SUPPRESS,
                        help="This directory will be used to generate "
                             "CodeChecker report directory files.")

    parser.add_argument('-t', '--type',
                        dest='type',
                        metavar='TYPE',
                        required=True,
                        choices=supported_converters,
                        default=argparse.SUPPRESS,
                        help="Specify the format of the code analyzer output. "
                             "Currently supported output types are: " +
                              ', '.join(supported_converters) + ".")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        dest='verbose',
                        help="Set verbosity level.")


def main():
    """ Warning to plist converter main command line. """
    parser = argparse.ArgumentParser(
        prog="warn-to-plist",
        description="Creates a CodeChecker report directory from the given "
                    "code analyzer output which can be stored to a "
                    "CodeChecker web server.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    __add_arguments_to_parser(parser)

    args = parser.parse_args()

    if 'verbose' in args and args.verbose:
        LOG.setLevel(logging.DEBUG)

    if 'input' in args and args.input:
        with open(args.input) as input_file:
            output = input_file.readlines()
    else:
        output = sys.stdin.readlines()

    output_to_plist(output, args.type, args.output_dir)


if __name__ == "__main__":
    main()
