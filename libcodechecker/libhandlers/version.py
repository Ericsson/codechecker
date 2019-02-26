# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Defines a subcommand for CodeChecker which prints version information.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse

from libcodechecker import logger
from libcodechecker import output_formatters


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker version',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Print the version of CodeChecker package that is "
                       "being used.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Print the version of CodeChecker package that is being used."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='table',
                        choices=output_formatters.USER_FORMATS,
                        help="The format to use when printing the version.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    Get and print the version information from the version config
    file and Thrift API definition.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

    output_format = args.output_format

    has_analyzer_version = False
    try:
        from libcodechecker.libhandlers import analyzer_version
        has_analyzer_version = True

        # Print analyzer version information.
        print("CodeChecker analyzer version:")
        analyzer_version.print_version(output_format)
    except Exception:
        pass

    try:
        from libcodechecker.libhandlers import webserver_version

        if has_analyzer_version:
            print()  # Print a new line to separate version information.

        # Print web server version information.
        print("CodeChecker web server version:")
        webserver_version.print_version(output_format)
    except Exception:
        pass
