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
import subprocess
import sys

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.analyzers import analyzer_types
from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA

from codechecker_common import logger
from codechecker_common import output_formatters
from codechecker_analyzer import env

LOG = logger.get_logger('system')


def get_diagtool_bin():
    """
    Return full path of diagtool.

    Select clang binary, check for a 'diagtool' binary next to the selected
    clang binary and return full path of this binary if it exists.
    """
    context = analyzer_context.get_context()
    clang_bin = context.analyzer_binaries.get(ClangSA.ANALYZER_NAME)

    if not clang_bin:
        return None

    # Resolve symlink.
    clang_bin = os.path.realpath(clang_bin)

    # Find diagtool next to the clang binary.
    diagtool_bin = os.path.join(os.path.dirname(clang_bin), 'diagtool')
    if os.path.exists(diagtool_bin):
        return diagtool_bin

    LOG.debug("'diagtool' can not be found next to the clang binary (%s)!",
              clang_bin)

    return None


def get_warnings(env=None):
    """
    Returns list of warning flags by using diagtool.
    """
    diagtool_bin = get_diagtool_bin()

    if not diagtool_bin:
        return []

    command = [diagtool_bin, 'tree']
    try:
        result = subprocess.check_output(command, env=env,
                                         universal_newlines=True)
        return parse_warnings(result)
    except (subprocess.CalledProcessError, OSError):
        return []


def parse_warnings(diagtool_output):
    """
    Parse diagtool warning list output and return a list of clang warnings.
    """
    warnings = []

    for line in diagtool_output.splitlines():
        if line.startswith('GREEN = enabled by default') or line == '':
            continue
        warnings.append(line.strip())

    return warnings


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
                       "status in the supported analyzers.",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': "The list of checkers that are enabled of disabled by "
                  "default can be edited by editing the file '" +
                  os.path.join(analyzer_context.get_context()
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
                             "specified. Currently supported analyzers are: " +
                             ', '.join(analyzer_types.
                                       supported_analyzers) + ".")

    if get_diagtool_bin():
        parser.add_argument('-w', '--warnings',
                            dest='show_warnings',
                            default=argparse.SUPPRESS,
                            action='store_true',
                            required=False,
                            help="Show available warning flags.")

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

    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    logger.setup_logger(args.verbose if 'verbose' in args else None, stream)

    # If nothing is set, list checkers for all supported analyzers.
    analyzers = args.analyzers \
        if 'analyzers' in args \
        else analyzer_types.supported_analyzers

    context = analyzer_context.get_context()
    working, errored = analyzer_types.check_supported_analyzers(analyzers,
                                                                context)

    analyzer_environment = env.extend(context.path_env_extra,
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
                sys.exit(1)

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

        show_warnings = True if 'show_warnings' in args and \
            args.show_warnings else False

        if show_warnings:
            severity = context.severity_map.get('clang-diagnostic-')
            for warning in get_warnings(analyzer_environment):
                if 'details' not in args:
                    rows.append([warning])
                else:
                    rows.append(['', warning, '-', severity, '-'])

    if rows:
        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))

    for analyzer_binary, reason in errored:
        LOG.error("Failed to get checkers for '%s'!"
                  "The error reason was: '%s'", analyzer_binary, reason)
        LOG.error("Please check your installation and the "
                  "'config/package_layout.json' file!")
