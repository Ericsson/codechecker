# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Execute analysis over an already existing build.json compilation database.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import json
import os
import shutil
import sys

from libcodechecker import logger
from libcodechecker import package_context
from libcodechecker import host_check
from libcodechecker.analyze import analyzer
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.log import log_parser
from libcodechecker.util import RawDescriptionDefaultHelpFormatter, \
    load_json_or_empty
from libcodechecker.analyze import skiplist_handler

LOG = logger.get_logger('system')


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
        'formatter_class': RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': """
Use the previously created JSON Compilation Database to perform an analysis on
the project, outputting analysis results in a machine-readable format.""",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': """
Compilation databases can be created by instrumenting your project's build via
'CodeChecker log'. To transform the results of the analysis to a human-friendly
format, please see the commands 'CodeChecker parse' or 'CodeChecker store'.""",

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
                        required=True,
                        default=argparse.SUPPRESS,
                        help="Store the analysis output in the given folder.")

    parser.add_argument('-t', '--type', '--output-format',
                        dest="output_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results should "
                             "use.")

    parser.add_argument('-q', '--quiet',
                        dest="quiet",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Do not print the output or error of the "
                             "analyzers to the standard output of "
                             "CodeChecker.")

    parser.add_argument('-c', '--clean',
                        dest="clean",
                        required=False,
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Delete analysis reports stored in the output "
                             "directory. (By default, CodeChecker would keep "
                             "reports and overwrites only those files that "
                             "were update by the current build command).")

    parser.add_argument('--report-hash',
                        dest="report_hash",
                        default=argparse.SUPPRESS,
                        required=False,
                        choices=['context-free'],
                        help="EXPERIMENTAL feature. "
                             "Specify the hash calculation method for "
                             "reports. If this option is not set, the default "
                             "calculation method for Clang Static Analyzer "
                             "will be context sensitive and for Clang Tidy it "
                             "will be context insensitive. If this option is "
                             "set to 'context-free' bugs will be identified "
                             "with the CodeChecker generated context free "
                             "hash for every analyzers. USE WISELY AND AT "
                             "YOUR OWN RISK!")

    parser.add_argument('-n', '--name',
                        dest="name",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Annotate the run analysis with a custom name in "
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
                               required=False,
                               default=argparse.SUPPRESS,
                               help="DEPRECATED. Always True. Retrieve "
                                    "compiler-specific configuration "
                                    "from the compilers themselves, and use "
                                    "them with Clang. This is used when the "
                                    "compiler on the system is special, e.g. "
                                    "when doing cross-compilation.")

    analyzer_opts.add_argument('--capture-analysis-output',
                               dest='capture_analysis_output',
                               action='store_true',
                               default=argparse.SUPPRESS,
                               required=False,
                               help="Store standard output and standard error "
                                    "of successful analyzer invocations "
                                    "into the '<OUTPUT_DIR>/success' "
                                    "directory.")

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

    analyzer_opts.add_argument('--tidy-config',
                               dest='tidy_config',
                               required=False,
                               default=argparse.SUPPRESS,
                               help="A file in YAML format containing the "
                                    "configuration of clang-tidy checkers. "
                                    "The file can be dumped by "
                                    "'CodeChecker analyzers --dump-config "
                                    "clang-tidy' command.")

    analyzer_opts.add_argument('--timeout',
                               type=int,
                               dest='timeout',
                               required=False,
                               default=argparse.SUPPRESS,
                               help="The amount of time (in seconds) that "
                                    "each analyzer can spend, individually, "
                                    "to analyze the project. If the analysis "
                                    "of a particular file takes longer than "
                                    "this time, the analyzer is killed and "
                                    "the analysis is considered as a failed "
                                    "one.")

    context = package_context.get_context()
    if host_check.is_ctu_capable(context):
        ctu_opts = parser.add_argument_group(
            "cross translation unit analysis arguments",
            """
These arguments are only available if the Clang Static Analyzer supports
Cross-TU analysis. By default, no CTU analysis is run when
'CodeChecker analyze' is called.""")

        ctu_modes = ctu_opts.add_mutually_exclusive_group()
        ctu_modes.add_argument('--ctu', '--ctu-all',
                               action='store_const',
                               const=[True, True],
                               dest='ctu_phases',
                               default=argparse.SUPPRESS,
                               help="Perform Cross Translation Unit (CTU) "
                                    "analysis, both 'collect' and 'analyze' "
                                    "phases. In this mode, the extra files "
                                    "created by 'collect' are cleaned up "
                                    "after the analysis.")

        ctu_modes.add_argument('--ctu-collect',
                               action='store_const',
                               const=[True, False],
                               dest='ctu_phases',
                               default=argparse.SUPPRESS,
                               help="Perform the first, 'collect' phase of "
                                    "Cross-TU analysis. This phase generates "
                                    "extra files needed by CTU analysis, and "
                                    "puts them into '<OUTPUT_DIR>/ctu-dir'. "
                                    "NOTE: If this argument is present, "
                                    "CodeChecker will NOT execute the "
                                    "analyzers!")

        ctu_modes.add_argument('--ctu-analyze',
                               action='store_const',
                               const=[False, True],
                               dest='ctu_phases',
                               default=argparse.SUPPRESS,
                               help="Perform the second, 'analyze' phase of "
                                    "Cross-TU analysis, using already "
                                    "available extra files in "
                                    "'<OUTPUT_DIR>/ctu-dir'. (These files "
                                    "will not be cleaned up in this mode.)")

        ctu_opts.add_argument('--ctu-reanalyze-on-failure',
                              action='store_true',
                              dest='ctu_reanalyze_on_failure',
                              default=argparse.SUPPRESS,
                              help="If Cross-TU analysis is enabled and fails "
                                   "for some reason, try to re analyze the "
                                   "same translation unit without "
                                   "Cross-TU enabled.")

    if host_check.is_statistics_capable(context):
        stat_opts = parser.add_argument_group(
            "EXPERIMENTAL statistics analysis feature arguments",
            """
These arguments are only available if the Clang Static Analyzer supports
Statistics-based analysis (e.g. statisticsCollector.ReturnValueCheck,
statisticsCollector.SpecialReturnValue checkers are available).""")

        stat_opts.add_argument('--stats-collect', '--stats-collect',
                               action='store',
                               default=argparse.SUPPRESS,
                               dest='stats_output',
                               help="EXPERIMENTAL feature. "
                                    "Perform the first, 'collect' phase of "
                                    "Statistical analysis. This phase "
                                    "generates extra files needed by "
                                    "statistics analysis, and "
                                    "puts them into "
                                    "'<STATS_OUTPUT>'."
                                    " NOTE: If this argument is present, "
                                    "CodeChecker will NOT execute the "
                                    "analyzers!")

        stat_opts.add_argument('--stats-use', '--stats-use',
                               action='store',
                               default=argparse.SUPPRESS,
                               dest='stats_dir',
                               help="EXPERIMENTAL feature. "
                                    "Use the previously generated statistics "
                                    "results for the analysis from the given "
                                    "'<STATS_DIR>'.")

        stat_opts.add_argument('--stats',
                               action='store_true',
                               default=argparse.SUPPRESS,
                               dest='stats_enabled',
                               help="EXPERIMENTAL feature. "
                                    "Perform both phases of "
                                    "Statistical analysis. This phase "
                                    "generates extra files needed by "
                                    "statistics analysis and enables "
                                    "the statistical checkers. "
                                    "No need to enable them explicitly.")

        stat_opts.add_argument('--stats-min-sample-count',
                               action='store',
                               default="10",
                               type=int,
                               dest='stats_min_sample_count',
                               help="EXPERIMENTAL feature. "
                                    "Minimum number of samples (function call"
                                    " occurrences) to be collected"
                                    " for a statistics to be relevant "
                                    "'<MIN-SAMPLE-COUNT>'.")

        stat_opts.add_argument('--stats-relevance-threshold',
                               action='store',
                               default="0.85",
                               type=float,
                               dest='stats_relevance_threshold',
                               help="EXPERIMENTAL feature. "
                                    "The minimum ratio of calls of function "
                                    "f that must have a certain property "
                                    "property to consider it true for that "
                                    "function (calculated as calls "
                                    "with a property/all calls)."
                                    " CodeChecker will warn for"
                                    " calls of f do not have that property."
                                    "'<RELEVANCE_THRESHOLD>'.")

    checkers_opts = parser.add_argument_group(
        "checker configuration",
        """
Checkers
------------------------------------------------
The analyzer performs checks that are categorized into families or "checkers".
See 'CodeChecker checkers' for the list of available checkers. You can
fine-tune which checkers to use in the analysis by setting the enabled and
disabled flags starting from the bigger groups and going inwards, e.g.
'-e core -d core.uninitialized -e core.uninitialized.Assign' will enable every
'core' checker, but only 'core.uninitialized.Assign' from the
'core.uninitialized' group. Please consult the manual for details. Disabling
certain checkers - such as the 'core' group - is unsupported by the LLVM/Clang
community, and thus discouraged.

Compiler warnings
------------------------------------------------
Compiler warnings are diagnostic messages that report constructions that are
not inherently erroneous but that are risky or suggest there may have been an
error. Compiler warnings are named 'clang-diagnostic-<warning-option>', e.g.
Clang warning controlled by '-Wliteral-conversion' will be reported with check
name 'clang-diagnostic-literal-conversion'. You can fine-tune which warnings to
use in the analysis by setting the enabled and disabled flags starting from the
bigger groups and going inwards, e.g. '-e Wunused -d Wno-unused-parameter' will
enable every 'unused' warnings except 'unused-parameter'. These flags should
start with a capital 'W' or 'Wno-' prefix followed by the waning name (E.g.:
'-e Wliteral-conversion', '-d Wno-literal-conversion'). By default '-Wall' and
'-Wextra' warnings are enabled. For more information see:
https://clang.llvm.org/docs/DiagnosticsReference.html.""")

    checkers_opts.add_argument('-e', '--enable',
                               dest="enable",
                               metavar='checker/group/profile',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker group) "
                                    "to BE USED in the analysis.")

    checkers_opts.add_argument('-d', '--disable',
                               dest="disable",
                               metavar='checker/group/profile',
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

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def __get_skip_handler(args):
    """
    Initialize and return a skiplist handler if
    there is a skip list file in the arguments.
    """
    try:
        if args.skipfile:
            LOG.debug_analyzer("Creating skiplist handler.")
            with open(args.skipfile) as skip_file:
                return skiplist_handler.SkipListHandler(skip_file.read())
    except AttributeError:
        LOG.debug_analyzer('Skip file was not set in the command line')


def __update_skip_file(args):
    """
    Remove previous skip file if there was any.
    """
    skip_file_to_send = os.path.join(args.output_path, 'skip_file')

    if os.path.exists(skip_file_to_send):
        os.remove(skip_file_to_send)

    if 'skipfile' in args:
        LOG.debug("Copying skip file %s to %s",
                  args.skipfile, skip_file_to_send)
        shutil.copyfile(args.skipfile, skip_file_to_send)


def main(args):
    """
    Perform analysis on the given logfiles and store the results in a machine-
    readable format.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

    if len(args.logfile) != 1:
        LOG.warning("Only one log file can be processed right now!")
        sys.exit(1)

    args.output_path = os.path.abspath(args.output_path)
    if os.path.exists(args.output_path) and \
            not os.path.isdir(args.output_path):
        LOG.error("The given output path is not a directory: " +
                  args.output_path)
        sys.exit(1)

    if 'enable_all' in args:
        LOG.info("'--enable-all' was supplied for this analysis.")

    # We clear the output directory in the following cases.
    ctu_dir = os.path.join(args.output_path, 'ctu-dir')
    if 'ctu_phases' in args and args.ctu_phases[0] and \
            os.path.isdir(ctu_dir):
        # Clear the CTU-dir if the user turned on the collection phase.
        LOG.debug("Previous CTU contents have been deleted.")
        shutil.rmtree(ctu_dir)

    if 'clean' in args and os.path.isdir(args.output_path):
        LOG.info("Previous analysis results in '{0}' have been removed, "
                 "overwriting with current result".format(args.output_path))
        shutil.rmtree(args.output_path)

    if not os.path.exists(args.output_path):
        os.makedirs(args.output_path)

    LOG.debug("args: " + str(args))
    LOG.debug("Output will be stored to: '" + args.output_path + "'")

    # Process the skip list if present.
    skip_handler = __get_skip_handler(args)

    # Parse the JSON CCDBs and retrieve the compile commands.
    actions = []
    for log_file in args.logfile:
        if not os.path.exists(log_file):
            LOG.error("The specified logfile '" + log_file + "' does not "
                      "exist!")
            continue

        actions += log_parser.parse_log(
            load_json_or_empty(log_file),
            skip_handler,
            os.path.join(args.output_path, 'compiler_info.json'))
    if len(actions) == 0:
        LOG.info("None of the specified build log files contained "
                 "valid compilation commands. No analysis needed...")
        sys.exit(1)

    context = package_context.get_context()
    metadata = {'action_num': len(actions),
                'command': sys.argv,
                'versions': {
                    'codechecker': "{0} ({1})".format(
                        context.package_git_tag,
                        context.package_git_hash)},
                'working_directory': os.getcwd(),
                'output_path': args.output_path,
                'result_source_files': {}}

    if 'name' in args:
        metadata['name'] = args.name

    # Update metadata dictionary with old values.
    metadata_file = os.path.join(args.output_path, 'metadata.json')
    if os.path.exists(metadata_file):
        metadata_prev = load_json_or_empty(metadata_file)
        metadata['result_source_files'] = \
            metadata_prev['result_source_files']

    analyzer.perform_analysis(args, skip_handler, context, actions, metadata)

    __update_skip_file(args)

    LOG.debug("Analysis metadata write to '" + metadata_file + "'")
    with open(metadata_file, 'w') as metafile:
        json.dump(metadata, metafile)

    # WARN: store command will search for this file!!!!
    compile_cmd_json = os.path.join(args.output_path, 'compile_cmd.json')
    try:
        source = os.path.abspath(args.logfile[0])
        target = os.path.abspath(compile_cmd_json)

        if source != target:
            shutil.copyfile(source, target)
    except shutil.Error:
        LOG.debug("Compilation database JSON file is the same.")
    except Exception:
        LOG.debug("Copying compilation database JSON file failed.")

    try:
        from libcodechecker import analyzer_statistics
        analyzer_statistics.collect(metadata, "analyze")
    except Exception:
        pass
