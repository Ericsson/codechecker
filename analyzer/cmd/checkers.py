# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
List the checkers available in the analyzers.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import os

from codechecker.analyze.analyzers import analyzer_types

from libcodechecker import package_context
from libcodechecker import logger
from libcodechecker import output_formatters
from libcodechecker.env import get_check_env

LOG = logger.get_logger('system')


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
                  os.path.join(package_context.get_context()
                               .package_root, 'config', 'config.json') + "'.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "List the checkers available for code analysis."
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
                        default=argparse.SUPPRESS,
                        action='store_true',
                        required=False,
                        help="Show details about the checker, such as "
                             "description, if available.")

    parser.add_argument('--profile',
                        dest='profile',
                        metavar='PROFILE/list',
                        required=False,
                        default=argparse.SUPPRESS,
                        help="List checkers enabled by the selected profile. "
                             "'list' is a special option showing details "
                             "about profiles collectively.")

    filters = parser.add_mutually_exclusive_group(required=False)

    filters.add_argument('--only-enabled',
                         dest='only_enabled',
                         default=argparse.SUPPRESS,
                         action='store_true',
                         help="Show only the enabled checkers.")

    filters.add_argument('--only-disabled',
                         dest='only_disabled',
                         default=argparse.SUPPRESS,
                         action='store_true',
                         help="Show only the disabled checkers.")

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='rows',
                        choices=output_formatters.USER_FORMATS,
                        help="The format to list the applicable checkers as.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    List the checkers available in the specified (or all supported) analyzers
    alongside with their description or enabled status in various formats.
    """

    logger.setup_logger(args.verbose if 'verbose' in args else None)

    # If nothing is set, list checkers for all supported analyzers.
    analyzers = args.analyzers \
        if 'analyzers' in args \
        else analyzer_types.supported_analyzers

    context = package_context.get_context()
    working, errored = analyzer_types.check_supported_analyzers(analyzers,
                                                                context)

    analyzer_environment = get_check_env(context.path_env_extra,
                                         context.ld_lib_path_extra)

    analyzer_config_map = analyzer_types.build_config_handlers(args,
                                                               context,
                                                               working)
    # List available checker profiles.
    if 'profile' in args and args.profile == 'list':
        if 'details' not in args:
            if args.output_format not in ['csv', 'json']:
                header = ['Profile name']
            else:
                header = ['profile_name']
        else:
            if args.output_format not in ['csv', 'json']:
                header = ['Profile name', 'Description']
            else:
                header = ['profile_name', 'description']

        rows = []
        for (profile, description) in context.available_profiles.items():
            if 'details' not in args:
                rows.append([profile])
            else:
                rows.append([profile, description])

        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))
        return

    # Use good looking different headers based on format.
    if 'details' not in args:
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
        analyzer_class = \
            analyzer_types.supported_analyzers[analyzer]

        checkers = analyzer_class.get_analyzer_checkers(config_handler,
                                                        analyzer_environment)
        default_checker_cfg = context.checker_config.get(
            analyzer + '_checkers')

        profile_checkers = None
        if 'profile' in args:
            if args.profile not in context.available_profiles:
                LOG.error("Checker profile '%s' does not exist!",
                          args.profile)
                LOG.error("To list available profiles, use '--profile list'.")
                return

            profile_checkers = [(args.profile, True)]

        config_handler.initialize_checkers(context.available_profiles,
                                           context.package_root,
                                           checkers,
                                           default_checker_cfg,
                                           profile_checkers)

        for checker_name, value in config_handler.checks().items():
            enabled, description = value

            if not enabled and 'profile' in args:
                continue

            if enabled and 'only_disabled' in args:
                continue
            elif not enabled and 'only_enabled' in args:
                continue

            if args.output_format != 'json':
                enabled = '+' if enabled else '-'

            if 'details' not in args:
                rows.append([checker_name])
            else:
                severity = context.severity_map.get(checker_name)
                rows.append([enabled, checker_name, analyzer,
                             severity, description])

    if len(rows) > 0:
        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))

    for analyzer_binary, reason in errored:
        LOG.error("Failed to get checkers for '%s'!"
                  "The error reason was: '%s'", analyzer_binary, reason)
        LOG.error("Please check your installation and the "
                  "'config/package_layout.json' file!")
