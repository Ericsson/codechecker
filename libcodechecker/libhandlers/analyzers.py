# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Subcommand module for the 'CodeChecker analyzers' command which lists the
analyzers available in CodeChecker.
"""

import argparse
import subprocess

from libcodechecker import logger
from libcodechecker import generic_package_context
from libcodechecker import output_formatters
from libcodechecker.analyze.analyzers import analyzer_types

LOG = logger.get_logger('analyze')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker analyzers',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Get the list of available and supported analyzers, "
                       "querying their version and actual binary executed.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "List supported and available analyzers."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('--all',
                        dest="all",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Show all supported analyzers, not just the "
                             "available ones.")

    parser.add_argument('--details',
                        dest="details",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Show details about the analyzers, not just "
                             "their names.")

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='rows',
                        choices=output_formatters.USER_FORMATS,
                        help="Specify the format of the output list.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    List the analyzers' basic information supported by CodeChecker.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

    context = generic_package_context.get_context()
    working, errored = \
        analyzer_types.check_supported_analyzers(
            analyzer_types.supported_analyzers,
            context)

    if args.output_format not in ['csv', 'json']:
        if 'details' not in args:
            header = ['Name']
        else:
            header = ['Name', 'Path', 'Version']
    else:
        if 'details' not in args:
            header = ['name']
        else:
            header = ['name', 'path', 'version_string']

    rows = []
    for analyzer in working:
        if 'details' not in args:
            rows.append([analyzer])
        else:
            binary = context.analyzer_binaries.get(analyzer)
            try:
                version = subprocess.check_output([binary,
                                                   '--version'])
            except (subprocess.CalledProcessError, OSError):
                version = 'ERROR'

            rows.append([analyzer,
                         binary,
                         version])

    if 'all' in args:
        for analyzer, err_reason in errored:
            if 'details' not in args:
                rows.append([analyzer])
            else:
                rows.append([analyzer,
                             context.analyzer_binaries.get(analyzer),
                             err_reason])

    if len(rows) > 0:
        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))
