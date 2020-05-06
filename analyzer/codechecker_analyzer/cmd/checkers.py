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
import subprocess
import sys

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.analyzers import analyzer_types
from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA

from codechecker_common import logger
from codechecker_common import output_formatters
from codechecker_analyzer import env
from codechecker_analyzer.analyzers.config_handler import CheckerState

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


def get_warnings(env=None):
    """
    Returns list of warning flags by using diagtool.
    """
    diagtool_bin = get_diagtool_bin()

    if not diagtool_bin:
        return []

    try:
        result = subprocess.check_output(
            [diagtool_bin, 'tree'],
            env=env,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore")
        return result.split()
    except (subprocess.CalledProcessError, OSError):
        return []


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
                        default=list(analyzer_types.supported_analyzers.
                                     keys()),
                        help="Show checkers only from the analyzers "
                             "specified.")

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

    parser.add_argument('--checker-config',
                        dest='checker_config',
                        default=argparse.SUPPRESS,
                        action='store_true',
                        required=False,
                        help="Show checker configuration options. These can "
                             "be given to 'CodeChecker analyze "
                             "--checker-config'.")

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
    logger.setup_logger(args.verbose if 'verbose' in args else None,
                        None if args.output_format == 'table' else 'stderr')

    context = analyzer_context.get_context()
    working_analyzers, errored = analyzer_types.check_supported_analyzers(
        args.analyzers,
        context)

    analyzer_environment = env.extend(context.path_env_extra,
                                      context.ld_lib_path_extra)

    analyzer_config_map = analyzer_types.build_config_handlers(
        args, context, working_analyzers)

    def uglify(text):
        """
        csv and json format output contain this non human readable header
        string: no CamelCase and no space.
        """
        return text.lower().replace(' ', '_')

    # List available checker profiles.
    if 'profile' in args and args.profile == 'list':
        if 'details' in args:
            header = ['Profile name', 'Description']
            rows = context.available_profiles.items()
        else:
            header = ['Profile name']
            rows = ([key] for key in context.available_profiles.keys())

        if args.output_format in ['csv', 'json']:
            header = list(map(uglify, header))

        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))
        return

    # List checker config options.
    if 'checker_config' in args:
        if 'details' in args:
            header = ['Option', 'Description']
        else:
            header = ['Option']

        if args.output_format in ['csv', 'json']:
            header = list(map(uglify, header))

        rows = []
        for analyzer in working_analyzers:
            config_handler = analyzer_config_map.get(analyzer)
            analyzer_class = analyzer_types.supported_analyzers[analyzer]

            configs = analyzer_class.get_checker_config(config_handler,
                                                        analyzer_environment)
            rows.extend((':'.join((analyzer, c[0])), c[1]) if 'details' in args
                        else (':'.join((analyzer, c[0])),) for c in configs)

        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))
        return

    # List available checkers.
    if 'details' in args:
        header = ['Enabled', 'Name', 'Analyzer', 'Severity', 'Description']
    else:
        header = ['Name']

    if args.output_format in ['csv', 'json']:
        header = list(map(uglify, header))

    rows = []
    for analyzer in working_analyzers:
        config_handler = analyzer_config_map.get(analyzer)
        analyzer_class = analyzer_types.supported_analyzers[analyzer]

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
            state, description = value

            if state != CheckerState.enabled and 'profile' in args:
                continue

            if state == CheckerState.enabled and 'only_disabled' in args:
                continue
            elif state != CheckerState.enabled and 'only_enabled' in args:
                continue

            if args.output_format == 'json':
                state = state == CheckerState.enabled
            else:
                state = '+' if state == CheckerState.enabled else '-'

            if 'details' in args:
                severity = context.severity_map.get(checker_name)
                rows.append([state, checker_name, analyzer,
                             severity, description])
            else:
                rows.append([checker_name])

        if 'show_warnings' in args:
            severity = context.severity_map.get('clang-diagnostic-')
            for warning in get_warnings(analyzer_environment):
                if 'details' in args:
                    rows.append(['', warning, '-', severity, '-'])
                else:
                    rows.append([warning])

    if rows:
        print(output_formatters.twodim_to_str(args.output_format,
                                              header, rows))

    for analyzer_binary, reason in errored:
        LOG.error("Failed to get checkers for '%s'!"
                  "The error reason was: '%s'", analyzer_binary, reason)
        LOG.error("Please check your installation and the "
                  "'config/package_layout.json' file!")
