# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Subcommand module for the 'CodeChecker analyzers' command which lists the
analyzers available in CodeChecker.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import subprocess

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.analyzers import analyzer_types

from libcodechecker import logger
from libcodechecker import output_formatters

LOG = logger.get_logger('system')


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

    context = analyzer_context.get_context()
    working, _ = analyzer_types.check_supported_analyzers(
        analyzer_types.supported_analyzers,
        context)

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

    parser.add_argument('--dump-config',
                        dest='dump_config',
                        required=False,
                        choices=list(working),
                        help="Dump the available checker options for the "
                             "given analyzer to the standard output. "
                             "Currently only clang-tidy supports this option. "
                             "The output can be redirected to a file named "
                             ".clang-tidy. If this file is placed to the "
                             "project directory then the options are applied "
                             "to the files under that directory. This config "
                             "file can also be provided via "
                             "'CodeChecker analyze' and 'CodeChecker check' "
                             "commands.")

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

    context = analyzer_context.get_context()
    working, errored = \
        analyzer_types.check_supported_analyzers(
            analyzer_types.supported_analyzers,
            context)

    if args.dump_config:
        binary = context.analyzer_binaries.get(args.dump_config)

        if args.dump_config == 'clang-tidy':
            subprocess.call([binary, '-dump-config', '-checks=*'])
        elif args.dump_config == 'clangsa':
            # TODO: Not supported by ClangSA yet!
            LOG.warning("'--dump-config clangsa' is not supported yet.")

        return

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
