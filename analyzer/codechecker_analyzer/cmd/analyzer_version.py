# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Defines a subcommand for CodeChecker which prints version information.
"""


import argparse
import json

from codechecker_analyzer import analyzer_context

from codechecker_common import logger
from codechecker_common.output import USER_FORMATS, twodim


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker analyzer version',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Print the version of CodeChecker analyzer package "
                       "that is being used.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Print the version of CodeChecker analyzer package that is "
                "being used."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='table',
                        choices=USER_FORMATS,
                        help="The format to use when printing the version.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def print_version(output_format=None):
    """
    Print analyzer version information in the given format.
    """
    context = analyzer_context.get_context()

    rows = [
        ("Base package version", context.version),
        ("Package build date", context.package_build_date),
        ("Git commit ID (hash)", context.package_git_hash),
        ("Git tag information", context.package_git_tag)
    ]

    if output_format == "json":
        # Use a special JSON format here, instead of
        # [ {"kind": "something", "version": "0.0.0"}, {"kind": "foo", ... } ]
        # do
        # { "something": "0.0.0", "foo": ... }
        print(json.dumps(dict(rows)))
    else:
        print(twodim.to_str(output_format, ["Kind", "Version"], rows))


def main(args):
    """
    Get and print the version information from the version config
    file and Thrift API definition.
    """
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    logger.setup_logger(args.verbose if 'verbose' in args else None, stream)

    print_version(args.output_format)
