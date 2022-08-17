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

from codechecker_common import logger
from codechecker_common.output import USER_FORMATS


LOG = logger.get_logger('system')


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
                        choices=USER_FORMATS,
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

    # Get analyzer version information if the module is available.
    analyzer_version = None
    try:
        from codechecker_analyzer.cmd.analyzer_version import Version
        analyzer_version = Version()
    except Exception:
        pass

    # Get web version information if the module is available.
    web_version = None
    try:
        from codechecker_web.cmd.web_version import Version
        web_version = Version()
    except Exception:
        pass

    # Print the version information.
    if output_format == "json":
        print(json.dumps({
            "analyzer":
                analyzer_version.to_dict() if analyzer_version else None,
            "web": web_version.to_dict() if web_version else None}))
    else:
        if analyzer_version:
            analyzer_version.print(output_format)
            print()

        if web_version:
            web_version.print(output_format)
