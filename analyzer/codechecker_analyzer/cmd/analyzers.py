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

from codechecker_report_converter import twodim

from codechecker_analyzer import analyzer_context
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

    parser.add_argument('--all',
                        dest="all",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="DEPRECATED.")

    parser.add_argument('--details',
                        dest="details",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="DEPRECATED.")

    parser.add_argument('--dump-config',
                        dest='dump_config',
                        required=False,
                        choices=analyzer_types.supported_analyzers,
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
                        choices=analyzer_types.supported_analyzers,
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
    _, errored = \
        analyzer_types.check_supported_analyzers(
            analyzer_types.supported_analyzers)

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
        elif args.dump_config == 'gcc':
            raise NotImplementedError('--dump-config')
        elif args.dump_config == 'infer':
            raise NotImplementedError('--dump-config')

        return

    def uglify(text):
        """
        csv and json format output contain this non human readable header
        string: no CamelCase and no space.
        """
        return text.lower().replace(' ', '_')

    if 'analyzer_config' in args:
        header = ['Option', 'Description']

        if args.output_format in ['csv', 'json']:
            header = list(map(uglify, header))

        analyzer_name = args.analyzer_config
        analyzer_class = analyzer_types.supported_analyzers[analyzer_name]

        configs = analyzer_class.get_analyzer_config()
        if not configs:
            LOG.warning("No analyzer configurations found for "
                        f"'{analyzer_name}'. If you suspsect this shouldn't "
                        "be the case, try to update your analyzer or check "
                        "whether CodeChecker found the intended binary.")

        rows = [(':'.join((analyzer_name, c[0])), c[1]) for c in configs]

        print(twodim.to_str(args.output_format, header, rows))

        for err_analyzer_name, err_reason in errored:
            if analyzer_name == err_analyzer_name:
                LOG.warning(
                    f"Can't analyze with '{analyzer_name}': {err_reason}")

        return

    header = ['Name', 'Path', 'Version']

    if args.output_format in ['csv', 'json']:
        header = list(map(uglify, header))

    rows = []
    for analyzer_name, analyzer_class in \
            analyzer_types.supported_analyzers.items():
        check_env = context.analyzer_env
        version = analyzer_class.get_binary_version(check_env)
        if not version:
            version = 'ERROR'

        binary = context.analyzer_binaries.get(analyzer_name)
        rows.append([analyzer_name, binary, version])

    assert rows
    print(twodim.to_str(args.output_format, header, rows))

    for analyzer_name, err_reason in errored:
        LOG.warning(f"Can't analyze with '{analyzer_name}': {err_reason}")
