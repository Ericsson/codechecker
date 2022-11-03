# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Subcommand module for the 'CodeChecker analyzers' command which lists the
analyzers available in CodeChecker.
"""


import argparse
import subprocess
import sys

from codechecker_report_converter import twodim

from codechecker_analyzer import analyzer_context
from codechecker_analyzer import env
from codechecker_analyzer.analyzers import analyzer_types

from codechecker_common import logger
from codechecker_common.output import USER_FORMATS

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
    working_analyzers, _ = analyzer_types.check_supported_analyzers(
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
                        choices=working_analyzers,
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

    parser.add_argument('--analyzer-config',
                        dest='analyzer_config',
                        required=False,
                        default=argparse.SUPPRESS,
                        choices=working_analyzers,
                        help="Show analyzer configuration options. These can "
                             "be given to 'CodeChecker analyze "
                             "--analyzer-config'.")

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='rows',
                        choices=USER_FORMATS,
                        help="Specify the format of the output list.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    List the analyzers' basic information supported by CodeChecker.
    """
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    logger.setup_logger(args.verbose if 'verbose' in args else None, stream)

    context = analyzer_context.get_context()
    working_analyzers, errored = \
        analyzer_types.check_supported_analyzers(
            analyzer_types.supported_analyzers,
            context)

    if args.dump_config:
        binary = context.analyzer_binaries.get(args.dump_config)

        if args.dump_config == 'clang-tidy':
            subprocess.call([binary, '-dump-config', '-checks=*'],
                            encoding="utf-8", errors="ignore")
        elif args.dump_config == 'clangsa':
            ret = subprocess.call([binary,
                                   '-cc1',
                                   '-analyzer-checker-option-help',
                                   '-analyzer-checker-option-help-alpha'],
                                  stderr=subprocess.PIPE,
                                  encoding="utf-8",
                                  errors="ignore")

            if ret:
                # This flag is supported from Clang 9.
                LOG.warning("'--dump-config clangsa' is not supported yet. "
                            "Please make sure that you are using Clang 9 or "
                            "newer.")
        elif args.dump_config == 'cppcheck':
            # TODO: Not supported by CppCheck yet!
            LOG.warning("'--dump-config cppcheck' is not supported.")

        return

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

    if 'analyzer_config' in args:
        if 'details' in args:
            header = ['Option', 'Description']
        else:
            header = ['Option']

        if args.output_format in ['csv', 'json']:
            header = list(map(uglify, header))

        analyzer = args.analyzer_config
        config_handler = analyzer_config_map.get(analyzer)
        analyzer_class = analyzer_types.supported_analyzers[analyzer]

        configs = analyzer_class.get_analyzer_config(config_handler,
                                                     analyzer_environment)
        if not configs:
            LOG.error("Failed to get analyzer configuration options for '%s' "
                      "analyzer! Please try to upgrade your analyzer version "
                      "to use this feature.", analyzer)
            sys.exit(1)

        rows = [(':'.join((analyzer, c[0])), c[1]) if 'details' in args
                else (':'.join((analyzer, c[0])),) for c in configs]

        print(twodim.to_str(args.output_format, header, rows))

        return

    if 'details' in args:
        header = ['Name', 'Path', 'Version']
    else:
        header = ['Name']

    if args.output_format in ['csv', 'json']:
        header = list(map(uglify, header))

    rows = []
    for analyzer in working_analyzers:
        if 'details' not in args:
            rows.append([analyzer])
        else:
            binary = context.analyzer_binaries.get(analyzer)
            try:
                version = subprocess.check_output(
                    [binary, '--version'], encoding="utf-8", errors="ignore")
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

    if rows:
        print(twodim.to_str(args.output_format, header, rows))
