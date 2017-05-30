# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Execute analysis over an already existing build.json compilation database.
"""

import argparse
import json
import os
import shutil
import sys

from libcodechecker import generic_package_context
from libcodechecker import util
from libcodechecker.analyze import log_parser
from libcodechecker.analyze import analyzer
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('ANALYZE')


class OrderedCheckersAction(argparse.Action):
    """
    Action to store enabled and disabled checkers
    and keep ordering from command line.

    Create separate lists based on the checker names for
    each analyzer.
    """

    # Users can supply invocation to 'codechecker-analyze' as follows:
    # -e core -d core.uninitialized -e core.uninitialized.Assign
    # We must support having multiple '-e' and '-d' options and the order
    # specified must be kept when the list of checkers are assembled for Clang.

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(OrderedCheckersAction, self).__init__(option_strings, dest,
                                                    **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):

        if 'ordered_checkers' not in namespace:
            namespace.ordered_checkers = []
        ordered_checkers = namespace.ordered_checkers
        ordered_checkers.append((value, self.dest == 'enable'))

        namespace.ordered_checkers = ordered_checkers


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker analyze',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Use the previously created JSON Compilation Database "
                       "to perform an analysis on the project, outputting "
                       "analysis results in a machine-readable format.",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': "Compilation databases can be created by instrumenting your "
                  "project's build via 'codechecker-log'. To transform the "
                  "results of the analysis to a human-friendly format, please "
                  "see the commands 'codechecker-parse' or "
                  "'codechecker-store'.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Execute the supported code analyzers for the files "
                "recorded in a JSON Compilation Database."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('logfile',
                        type=str,
                        nargs='+',
                        help="Path to the JSON compilation command database "
                             "files which were created during the build. "
                             "The analyzers will check only the files "
                             "registered in these build databases.")

    parser.add_argument('-j', '--jobs',
                        type=int,
                        dest="jobs",
                        required=False,
                        default=1,
                        help="Number of threads to use in analysis. More "
                             "threads mean faster analysis at the cost of "
                             "using more memory.")

    parser.add_argument('-i', '--ignore', '--skip',
                        dest="skipfile",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Path to the Skipfile dictating which project "
                             "files should be omitted from analysis. Please "
                             "consult the User guide on how a Skipfile "
                             "should be laid out.")

    parser.add_argument('-o', '--output',
                        dest="output_path",
                        required=False,
                        default=os.path.join(util.get_default_workspace(),
                                             'reports'),
                        help="Store the analysis output in the given folder.")

    parser.add_argument('-t', '--type', '--output-format',
                        dest="output_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results should "
                             "use.")

    parser.add_argument('-n', '--name',
                        dest="name",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Annotate the ran analysis with a custom name in "
                             "the created metadata file.")

    analyzer_opts = parser.add_argument_group("analyzer arguments")

    analyzer_opts.add_argument('--analyzers',
                               nargs='+',
                               dest='analyzers',
                               metavar='ANALYZER',
                               required=False,
                               choices=analyzer_types.supported_analyzers,
                               default=argparse.SUPPRESS,
                               help="Run analysis only with the analyzers "
                                    "specified. Currently supported analyzers "
                                    "are: " +
                                    ', '.join(analyzer_types.
                                              supported_analyzers) + ".")

    analyzer_opts.add_argument('--add-compiler-defaults',
                               action='store_true',
                               default=False,
                               required=False,
                               help="Retrieve compiler-specific configuration "
                                    "from the compilers themselves, and use "
                                    "them with Clang. This is used when the "
                                    "compiler on the system is special, e.g. "
                                    "when doing cross-compilation.")

    analyzer_opts.add_argument('--saargs',
                               dest="clangsa_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="File containing argument which will be "
                                    "forwarded verbatim for the Clang Static "
                                    "Analyzer.")

    analyzer_opts.add_argument('--tidyargs',
                               dest="tidy_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="File containing argument which will be "
                                    "forwarded verbatim for Clang-Tidy.")

    checkers_opts = parser.add_argument_group(
        "checker configuration",
        "See 'codechecker-checkers' for the list of available checkers. "
        "You can fine-tune which checkers to use in the analysis by setting "
        "the enabled and disabled flags starting from the bigger groups "
        "and going inwards, e.g. '-e core -d core.uninitialized -e "
        "core.uninitialized.Assign' will enable every 'core' checker, but "
        "only 'core.uninitialized.Assign' from the 'core.uninitialized' "
        "group. Please consult the manual for details. Disabling certain "
        "checkers - such as the 'core' group - is unsupported by the LLVM/"
        "Clang community, and thus discouraged.")

    checkers_opts.add_argument('-e', '--enable',
                               dest="enable",
                               metavar='checker/checker-group',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker group) "
                                    "to BE USED in the analysis.")

    checkers_opts.add_argument('-d', '--disable',
                               dest="disable",
                               metavar='checker/checker-group',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker group) "
                                    "to BE PROHIBITED from use in the "
                                    "analysis.")

    checkers_opts.add_argument('--enable-all',
                               dest="enable_all",
                               action='store_true',
                               required=False,
                               default=argparse.SUPPRESS,
                               help="Force the running analyzers to use "
                                    "almost every checker available. The "
                                    "checker groups 'alpha.', 'debug.' and "
                                    "'osx.' (on Linux) are NOT enabled "
                                    "automatically and must be EXPLICITLY "
                                    "specified. WARNING! Enabling all "
                                    "checkers might result in the analysis "
                                    "losing precision and stability, and "
                                    "could even result in a total failure of "
                                    "the analysis. USE WISELY AND AT YOUR "
                                    "OWN RISK!")

    add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    Perform analysis on the given logfiles and store the results in a machine-
    readable format.
    """

    context = generic_package_context.get_context()

    # Parse the JSON CCDBs and retrieve the compile commands.
    actions = []

    for log_file in args.logfile:
        if not os.path.exists(log_file):
            LOG.error("The specified logfile '" + log_file + "' does not "
                      "exist!")
            continue

        actions += log_parser.parse_log(log_file,
                                        args.add_compiler_defaults)

    if len(actions) == 0:
        LOG.info("None of the specified build log files contained "
                 "valid compilation commands. No analysis needed...")
        return

    if 'enable_all' in args:
        LOG.info("'--enable-all' was supplied for this analysis.")

    # Run the analysis.
    args.output_path = os.path.abspath(args.output_path)
    if os.path.isdir(args.output_path):
        LOG.info("Previous analysis results in '{0}' have been "
                 "removed, overwriting with current result".
                 format(args.output_path))
        shutil.rmtree(args.output_path)
    os.makedirs(args.output_path)

    LOG.debug("Output will be stored to: '" + args.output_path + "'")

    metadata = {'action_num': len(actions),
                'command': sys.argv,
                'versions': {
                    'codechecker': "{0} ({1})".format(context.package_git_tag,
                                                      context.package_git_hash)
                },
                'working_directory': os.getcwd(),
                'output_path': args.output_path}

    if 'name' in args:
        metadata['name'] = args.name

    if 'skipfile' in args:
        # Skip information needs to be saved because reports in a header
        # can only be skipped by the report-server used in 'store' later
        # on if this information is persisted.
        with open(args.skipfile, 'r') as skipfile:
            metadata['skip_data'] = [l.strip() for l in skipfile.readlines()]

    analyzer.perform_analysis(args, context, actions, metadata)

    metadata_path = os.path.join(args.output_path, 'metadata.json')
    LOG.debug("Analysis metadata write to '" + metadata_path + "'")
    with open(metadata_path, 'w') as metafile:
        json.dump(metadata, metafile)
