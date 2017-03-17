# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
List the checkers available in the analyzers.
"""

import argparse
import os

from libcodechecker import generic_package_context
from libcodechecker import output_formatters
from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('CHECKERS')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker checkers',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Get the list of checkers available and their enabled "
                       "status in the supported analyzers. Currently "
                       "supported analyzers are: " +
                       ', '.join(analyzer_types.supported_analyzers) +
                       ".",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': "The list of checkers that are enabled of disabled by "
                  "default can be edited by editing the file '" +
                  os.path.join(generic_package_context.get_context()
                               .package_root, 'config', 'config.json') + "'.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "List the checkers available in code analysis."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('--analyzers',
                        nargs='+',
                        dest='analyzers',
                        metavar='ANALYZER',
                        required=False,
                        choices=analyzer_types.supported_analyzers,
                        default=argparse.SUPPRESS,
                        help="Show checkers only from the analyzers "
                             "specified.")

    parser.add_argument('--details',
                        dest='details',
                        default=False,
                        action='store_true',
                        required=False,
                        help="Show details about the checker, such as "
                             "description, if available.")

    filters = parser.add_mutually_exclusive_group(required=False)

    filters.add_argument('--only-enabled',
                         dest='only_enabled',
                         default=False,
                         action='store_true',
                         help="Show only the enabled checkers.")

    filters.add_argument('--only-disabled',
                         dest='only_disabled',
                         default=False,
                         action='store_true',
                         help="Show only the disabled checkers.")

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='rows',
                        choices=output_formatters.USER_FORMATS,
                        help="The format to list the applicable checkers as.")

    add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    List the checkers available in the specified (or all supported) analyzers
    alongside with their description or enabled status in various formats.
    """

    # If nothing is set, list checkers for all supported analyzers.
    analyzers = args.analyzers \
        if 'analyzers' in args \
        else analyzer_types.supported_analyzers

    context = generic_package_context.get_context()
    working, errored = analyzer_types.check_supported_analyzers(analyzers,
                                                                context)

    analyzer_environment = analyzer_env.get_check_env(
        context.path_env_extra, context.ld_lib_path_extra)

    analyzer_config_map = analyzer_types.build_config_handlers(args,
                                                               context,
                                                               working)

    # Use good looking different headers based on format.
    if not args.details:
        if args.output_format not in ['csv', 'json']:
            header = ['Name']
        else:
            header = ['name']
    else:
        if args.output_format not in ['csv', 'json']:
            header = ['', 'Name', 'Analyzer', 'Severity', 'Description']
        else:
            header = ['enabled', 'name', 'analyzer', 'severity', 'description']

    rows = []
    for analyzer in working:
        config_handler = analyzer_config_map.get(analyzer)
        source_analyzer = \
            analyzer_types.construct_analyzer_type(analyzer,
                                                   config_handler,
                                                   None)

        checkers = source_analyzer.get_analyzer_checkers(config_handler,
                                                         analyzer_environment)
        default_checker_cfg = context.default_checkers_config.get(
            analyzer + '_checkers')
        analyzer_types.initialize_checkers(config_handler,
                                           checkers,
                                           default_checker_cfg)

        for checker_name, value in config_handler.checks().items():
            enabled, description = value

            if enabled and args.only_disabled:
                continue
            elif not enabled and args.only_enabled:
                continue

            if args.output_format != 'json':
                enabled = '+' if enabled else '-'

            if not args.details:
                rows.append([checker_name])
            else:
                severity = context.severity_map.get(checker_name,
                                                    'UNSPECIFIED')
                rows.append([enabled, checker_name, analyzer,
                             severity, description])

    if len(rows) > 0:
        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))

    for analyzer_binary, reason in errored:
        LOG.error("Failed to get checkers for '" + analyzer_binary +
                  "'! The error reason was: '" + reason + "'")
        LOG.error("Please check your installation and the "
                  "'config/package_layout.json' file!")
