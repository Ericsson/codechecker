#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import argparse
import os
import sys

# If we run this script in an environment where 'codechecker_report_converter'
# module is not available we should add the grandparent directory of this file
# to the system path.
if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath(
        os.path.join(__file__, *[os.path.pardir] * 4)))

from codechecker_report_converter.report.output.html.html import HtmlBuilder, \
    parse


def __add_arguments_to_parser(parser: argparse.ArgumentParser):
    parser.add_argument('input',
                        type=str,
                        nargs='+',
                        metavar='file/folder',
                        help="Analyzer result file(s) or folders containing "
                             "analysis results which should be parsed.")

    parser.add_argument('-o', '--output',
                        dest="output_dir",
                        required=True,
                        help="Generate HTML output files in the given folder.")

    curr_file_dir = os.path.dirname(os.path.realpath(__file__))
    parser.add_argument('-l', '--layout',
                        dest="layout_dir",
                        required=False,
                        default=os.path.join(curr_file_dir, 'static'),
                        help="Directory which contains dependency HTML, CSS "
                             "and JavaScript files.")


def main():
    """ Report to HTML main command line. """
    parser = argparse.ArgumentParser(
        prog="plist-to-html",
        description="Parse and create HTML files from one or more analyzer "
                    "result files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    __add_arguments_to_parser(parser)

    args = parser.parse_args()

    if isinstance(args.input, str):
        args.input = [args.input]

    # Source files which modification time changed since the last analysis.
    changed_source_files = set()

    html_builder = HtmlBuilder(args.layout_dir)
    for input_path in args.input:
        changed_files = parse(input_path, args.output_dir, args.layout_dir,
                              html_builder)
        changed_source_files.update(changed_files)

    html_builder.create_index_html(args.output_dir)
    html_builder.create_statistics_html(args.output_dir)

    print('\nTo view statistics in a browser run:\n> firefox {0}'.format(
        os.path.join(args.output_dir, 'statistics.html')))

    print('\nTo view the results in a browser run:\n> firefox {0}'.format(
        os.path.join(args.output_dir, 'index.html')))

    if changed_source_files:
        changed_files = '\n'.join([' - ' + f for f in changed_source_files])
        print("\nThe following source file contents changed since the "
              "latest analysis:\n{0}\nPlease analyze your project again to "
              "update the reports!".format(changed_files))


if __name__ == "__main__":
    main()
