# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Check implements a wrapper over 'log' + 'analyze' + 'parse', essentially
giving an easy way to perform analysis from a log command and print results to
stdout.
"""

import argparse
import os
import shutil
import sys
import tempfile

from codechecker_analyzer.analyzers import analyzer_types
from codechecker_analyzer.arg import \
    OrderedCheckersAction, OrderedConfigAction, \
    analyzer_config, checker_config, existing_abspath

from codechecker_analyzer.cmd.analyze import \
    EPILOG_ENV_VAR as analyzer_epilog_env_var, \
    EPILOG_ISSUE_HASHES as analyzer_epilog_issue_hashes

from codechecker_analyzer.cmd.log import \
    EPILOG_ENV_VAR as log_epilog_env_var

from codechecker_analyzer.cmd.parse import \
    EPILOG_ENV_VAR as parse_epilog_env_var

from codechecker_common import arg, cmd_config, logger
from codechecker_common.compatibility.multiprocessing import cpu_count
from codechecker_common.source_code_comment_handler import \
    REVIEW_STATUS_VALUES


LOG = logger.get_logger('system')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """
    return {
        'prog': 'CodeChecker check',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': """
Run analysis for a project with printing results immediately on the standard
output. Check only needs a build command or an already existing logfile and
performs every step of doing the analysis in batch.""",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': f"""
Environment variables
------------------------------------------------
Environment variables for 'CodeChecker log' command:
{log_epilog_env_var}

Environment variables for 'CodeChecker analyze' command:
{analyzer_epilog_env_var}

Environment variables for 'CodeChecker parse' command:
{parse_epilog_env_var}

{analyzer_epilog_issue_hashes}

Exit status
------------------------------------------------
0 - No report
1 - CodeChecker error
2 - At least one report emitted by an analyzer
3 - Analysis of at least one translation unit failed
128+signum - Terminating on a fatal signal whose number is signum

If you wish to reuse the logfile resulting from executing the build, see
'CodeChecker log'. To keep analysis results for later, see and use
'CodeChecker analyze'. To print human-readable output from previously saved
analysis results, see 'CodeChecker parse'. 'CodeChecker check' exposes a
wrapper calling these three commands in succession. Please make sure your build
command actually builds the files -- it is advised to execute builds on empty
trees, aka. after a 'make clean', as CodeChecker only analyzes files that had
been used by the build system.
""",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Perform analysis on a project and print results to standard "
                "output."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('-o', '--output',
                        type=str,
                        dest="output_dir",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Store the analysis output in the given folder. "
                             "If it is not given then the results go into a "
                             "temporary directory which will be removed after "
                             "the analysis.")

    parser.add_argument('-t', '--type', '--output-format',
                        dest="output_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results "
                             "should use.")

    parser.add_argument('-q', '--quiet',
                        dest="quiet",
                        action='store_true',
                        required=False,
                        default=argparse.SUPPRESS,
                        help="If specified, the build tool's and the "
                             "analyzers' output will not be printed to the "
                             "standard output.")

    parser.add_argument('--keep-gcc-include-fixed',
                        dest="keep_gcc_include_fixed",
                        required=False,
                        action='store_true',
                        default=False,
                        help="There are some implicit include paths which are "
                             "only used by GCC (include-fixed). This flag "
                             "determines whether these should be kept among "
                             "the implicit include paths.")

    parser.add_argument('--keep-gcc-intrin',
                        dest="keep_gcc_intrin",
                        required=False,
                        action='store_true',
                        default=False,
                        help="There are some implicit include paths which "
                             "contain GCC-specific header files (those "
                             "which end with intrin.h). This flag determines "
                             "whether these should be kept among the implicit "
                             "include paths. Use this flag if Clang analysis "
                             "fails with error message related to __builtin "
                             "symbols.")

    parser.add_argument('--add-gcc-include-dirs-with-isystem',
                        dest="add_gcc_include_dirs_with_isystem",
                        required=False,
                        action='store_true',
                        default=False,
                        help="Implicit include directories are appended to "
                             "the analyzer command with -idirafter. If "
                             "-isystem is needed instead, as it was used "
                             "before CodeChecker 6.24.1, this flag can be "
                             "used.")

    log_args = parser.add_argument_group(
        "log arguments",
        """
Specify how the build information database should be obtained. You need to
specify either an already existing log file, or a build command which will be
used to generate a log file on the fly.""")

    log_args = log_args.add_mutually_exclusive_group(required=True)

    log_args.add_argument('-b', '--build',
                          type=str,
                          dest="command",
                          default=argparse.SUPPRESS,
                          help="Execute and record a build command. Build "
                               "commands can be simple calls to 'g++' or "
                               "'clang++' or 'make', but a more complex "
                               "command, or the call of a custom script file "
                               "is also supported.")

    log_args.add_argument('-l', '--logfile',
                          type=str,
                          dest="logfile",
                          default=argparse.SUPPRESS,
                          help="Use an already existing JSON compilation "
                               "command database file specified at this path.")

    analyzer_opts = parser.add_argument_group("analyzer arguments")
    analyzer_opts.add_argument('-j', '--jobs',
                               type=int,
                               dest="jobs",
                               required=False,
                               default=cpu_count(),
                               help="Number of threads to use in analysis. "
                                    "More threads mean faster analysis at "
                                    "the cost of using more memory.")

    analyzer_opts.add_argument('-c', '--clean',
                               dest="clean",
                               required=False,
                               action='store_true',
                               default=argparse.SUPPRESS,
                               help="Delete analysis reports stored in the "
                                    "output directory. (By default, "
                                    "CodeChecker would keep reports and "
                                    "overwrites only those files that were "
                                    "update by the current build command).")

    parser.add_argument('--compile-uniqueing',
                        type=str,
                        dest="compile_uniqueing",
                        default="none",
                        required=False,
                        help="Specify the method the compilation "
                             "actions in the  compilation database are "
                             "uniqued before analysis. "
                             "CTU analysis works properly only if "
                             "there is exactly one "
                             "compilation action per source file. "
                             "none(default in non CTU mode): "
                             "no uniqueing is done. "
                             "strict: no uniqueing is done, "
                             "and an error is given if "
                             "there is more than one compilation "
                             "action for a source file. "
                             "symlink: recognizes symlinks and removes "
                             "duplication in the compilation database to "
                             "ensure that each source file is "
                             "analyzed only once. "
                             "alpha(default in CTU mode): If there is more "
                             "than one compilation action for a source "
                             "file, only the one is kept that belongs to the "
                             "alphabetically first "
                             "compilation target. "
                             "If none of the above given, "
                             "this parameter should "
                             "be a python regular expression. "
                             "If there is more than one compilation action "
                             "for a source, "
                             "only the one is kept which matches the "
                             "given python regex. If more than one "
                             "matches an error is given. "
                             "The whole compilation "
                             "action text is searched for match.")

    analyzer_opts.add_argument('--report-hash',
                               dest="report_hash",
                               default=argparse.SUPPRESS,
                               required=False,
                               choices=[
                                   'context-free',
                                   'context-free-v2',
                                   'diagnostic-message'],
                               help="R|Specify the hash calculation method "
                                    "for reports. By default the calculation "
                                    "method for Clang Static Analyzer is "
                                    "context sensitive and for Clang Tidy it "
                                    "is context insensitive.\nYou can use the "
                                    "following calculation methods:\n"
                                    "- context-free: there was a bug and for "
                                    "Clang Tidy not the context free hash "
                                    "was generated (kept for backward "
                                    "compatibility).\n"
                                    "- context-free-v2: context free hash is "
                                    "used for ClangSA and Clang Tidy.\n"
                                    "- diagnostic-message: context free hash "
                                    "with bug step messages is used for "
                                    "ClangSA and Clang Tidy.\n"
                                    "See the 'issue hashes' section of the "
                                    "help message of this command below for "
                                    "more information.\n"
                                    "USE WISELY AND AT YOUR OWN RISK!")

    skip_mode = parser.add_argument_group("file filter arguments")
    skip_mode.add_argument('-i', '--ignore', '--skip',
                           dest="skipfile",
                           required=False,
                           default=argparse.SUPPRESS,
                           help="Path to the Skipfile dictating which project "
                                "files should be omitted from analysis. "
                                "Please consult the User guide on how a "
                                "Skipfile should be laid out.")

    skip_mode.add_argument('--drop-reports-from-skipped-files',
                           dest="drop_skipped_reports",
                           required=False,
                           action='store_true',
                           default=False,
                           help="Filter our reports from files that were  "
                                "skipped from the analysis.")

    skip_mode.add_argument('--file',
                           nargs='+',
                           dest="files",
                           metavar='FILE',
                           required=False,
                           default=argparse.SUPPRESS,
                           help="Analyze only the given file(s) not the whole "
                                "compilation database. Absolute directory "
                                "paths should start with '/', relative "
                                "directory paths should start with '*' and "
                                "it can contain path glob pattern. "
                                "Example: '/path/to/main.cpp', 'lib/*.cpp', "
                                "*/test*'.")

    analyzer_opts.add_argument('--analyzers',
                               nargs='+',
                               dest='analyzers',
                               metavar='ANALYZER',
                               required=False,
                               choices=analyzer_types.supported_analyzers,
                               default=None,
                               help="Run analysis only with the analyzers "
                                    "specified. Currently supported analyzers "
                                    "are: " +
                                    ', '.join(analyzer_types.
                                              supported_analyzers) + ".")

    analyzer_opts.add_argument('--capture-analysis-output',
                               dest='capture_analysis_output',
                               action='store_true',
                               default=argparse.SUPPRESS,
                               required=False,
                               help="Store standard output and standard error "
                                    "of successful analyzer invocations "
                                    "into the '<OUTPUT_DIR>/success' "
                                    "directory.")

    analyzer_opts.add_argument('--generate-reproducer',
                               dest='generate_reproducer',
                               action='store_true',
                               default=argparse.SUPPRESS,
                               required=False,
                               help="Collect all necessary information for "
                                    "reproducing an analysis action. The "
                                    "gathered files will be stored in a "
                                    "folder named 'reproducer' under the "
                                    "report directory. When this flag is "
                                    "used, 'failed' directory remains empty.")

    cmd_config.add_option(analyzer_opts)

    # TODO: One day, get rid of these. See Issue #36, #427.
    analyzer_opts.add_argument('--cppcheckargs',
                               dest="cppcheck_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="File containing argument which will be "
                                    "forwarded verbatim for Cppcheck.")

    analyzer_opts.add_argument('--saargs',
                               dest="clangsa_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="File containing argument which will be "
                                    "forwarded verbatim for the Clang Static "
                                    "analyzer.")

    analyzer_opts.add_argument('--tidyargs',
                               dest="tidy_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="File containing argument which will be "
                                    "forwarded verbatim for the Clang-Tidy "
                                    "analyzer.")

    analyzer_opts.add_argument('--tidy-config',
                               dest='tidy_config',
                               required=False,
                               default=argparse.SUPPRESS,
                               help="DEPRECATED. "
                                    "A file in YAML format containing the "
                                    "configuration of clang-tidy checkers. "
                                    "The file can be dumped by "
                                    "'CodeChecker analyzers --dump-config "
                                    "clang-tidy' command.")

    analyzer_opts.add_argument('--analyzer-config',
                               type=analyzer_config,
                               dest='analyzer_config',
                               nargs='*',
                               action=OrderedConfigAction,
                               default=argparse.SUPPRESS,
                               help="Analyzer configuration options in the "
                                    "following format: analyzer:key=value. "
                                    "The collection of the options can be "
                                    "printed with "
                                    "'CodeChecker analyzers "
                                    "--analyzer-config'.\n"
                                    "If the file at --tidyargs "
                                    "contains a -config flag then those "
                                    "options extend these.\n"
                                    "To use an analyzer configuration file "
                                    "in case of Clang Tidy (.clang-tidy) use "
                                    "the "
                                    "'clang-tidy:take-config-from-directory="
                                    "true' option. It will skip setting the "
                                    "'-checks' parameter of the clang-tidy "
                                    "binary.")

    analyzer_opts.add_argument('--checker-config',
                               type=checker_config,
                               dest='checker_config',
                               nargs='*',
                               action=OrderedConfigAction,
                               default=argparse.SUPPRESS,
                               help="Checker configuration options in the "
                                    "following format: analyzer:key=value. "
                                    "The collection of the options can be "
                                    "printed with "
                                    "'CodeChecker checkers --checker-config'.")

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

    analyzer_opts.add_argument('--review-status-config',
                               dest="review_status_config",
                               required=False,
                               type=existing_abspath,
                               default=argparse.SUPPRESS,
                               help="Path of review_status.yaml config file "
                                    "which contains review status settings "
                                    "assigned to specific directories, "
                                    "checkers, bug hashes.")

    clang_has_z3 = analyzer_types.is_z3_capable()

    if clang_has_z3:
        analyzer_opts.add_argument('--z3',
                                   dest='enable_z3',
                                   choices=['on', 'off'],
                                   default='off',
                                   help="Enable Z3 as the solver backend. "
                                        "This allows reasoning over more "
                                        "complex queries, but performance is "
                                        "much worse than the default "
                                        "range-based constraint solver "
                                        "system. WARNING: Z3 as the only "
                                        "backend is a highly experimental "
                                        "and likely unstable feature.")

    clang_has_z3_refutation = analyzer_types.is_z3_refutation_capable()

    if clang_has_z3_refutation:
        analyzer_opts.add_argument('--z3-refutation',
                                   dest='enable_z3_refutation',
                                   choices=['on', 'off'],
                                   default='on' if clang_has_z3_refutation
                                   else 'off',
                                   help="Switch on/off the Z3 SMT Solver "
                                        "backend to "
                                        "reduce false positives. The results "
                                        "of the ranged based constraint "
                                        "solver in the Clang Static Analyzer "
                                        "will be cross checked with the Z3 "
                                        "SMT solver. This should not cause "
                                        "that much of a slowdown compared to "
                                        "using only the Z3 solver.")

    if analyzer_types.is_ctu_capable():
        ctu_opts = parser.add_argument_group(
            "cross translation unit analysis arguments",
            """
These arguments are only available if the Clang Static Analyzer supports
Cross-TU analysis. By default, no CTU analysis is run when 'CodeChecker check'
is called.""")

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
                              help="If Cross-TU analysis is enabled and "
                                   "fails for some reason, try to re analyze "
                                   "the same translation unit without "
                                   "Cross-TU enabled.")

        # Only check for AST loading modes if CTU is available.
        if analyzer_types.is_ctu_on_demand_available():
            ctu_opts.add_argument('--ctu-ast-mode',
                                  action='store',
                                  dest='ctu_ast_mode',
                                  choices=['load-from-pch', 'parse-on-demand'],
                                  default=argparse.SUPPRESS,
                                  help="Choose the way ASTs are loaded during "
                                       "CTU analysis. Only available if CTU "
                                       "mode is enabled. Mode 'load-from-pch' "
                                       "generates PCH format serialized ASTs "
                                       "during the 'collect' phase. Mode "
                                       "'parse-on-demand' only generates the "
                                       "invocations needed to parse the ASTs. "
                                       "Mode 'load-from-pch' can use "
                                       "significant disk-space for the "
                                       "serialized ASTs, while mode "
                                       "'parse-on-demand' can incur some "
                                       "runtime CPU overhead in the second "
                                       "phase of the analysis. (default: "
                                       "parse-on-demand)")

    if analyzer_types.is_statistics_capable():
        stat_opts = parser.add_argument_group(
            "Statistics analysis feature arguments",
            """
These arguments are only available if the Clang Static Analyzer supports
Statistics-based analysis (e.g. statisticsCollector.ReturnValueCheck,
statisticsCollector.SpecialReturnValue checkers are available).""")

        stat_opts.add_argument('--stats-collect', '--stats-collect',
                               action='store',
                               default=argparse.SUPPRESS,
                               dest='stats_output',
                               help="Perform the first, 'collect' phase of "
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
                               help="Use the previously generated statistics "
                                    "results for the analysis from the given "
                                    "'<STATS_DIR>'.")

        stat_opts.add_argument('--stats',
                               action='store_true',
                               default=argparse.SUPPRESS,
                               dest='stats_enabled',
                               help="Perform both phases of "
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
                               help="Minimum number of samples (function call"
                                    " occurrences) to be collected"
                                    " for a statistics to be relevant.")

        stat_opts.add_argument('--stats-relevance-threshold',
                               action='store',
                               default="0.85",
                               type=float,
                               dest='stats_relevance_threshold',
                               help="The minimum ratio of calls of function "
                                    "f that must have a certain property "
                                    "property to consider it true for that "
                                    "function (calculated as calls "
                                    "with a property/all calls)."
                                    " CodeChecker will warn for"
                                    " calls of f do not have that property.")

    checkers_opts = parser.add_argument_group(
        "checker configuration",
        """
Checkers
------------------------------------------------
An analyzer checks the source code with the help of checkers. Checkers
implement a specific rule, such as "don't divide by zero", and emit a warning
if the corresponding rule is violated. Available checkers can be listed by
'CodeChecker checkers'.

Checkers are grouped by CodeChecker via labels (described below), and sometimes
by their analyzer tool. An example for the latter is 'clangsa', which orders
checkers in a package hierarchy (e.g. in 'core.uninitialized.Assign', 'core'
and 'core.uninitialized' are packages).

Compiler warnings and errors
------------------------------------------------
Compiler warnings are diagnostic messages that report constructions that are
not inherently erroneous but that are risky or suggest there may have been an
error. However, CodeChecker views them as regular checkers.

Compiler warning names are transformed by CodeChecker to reflect the analyzer
name. For example, '-Wliteral-conversion' from clang-tidy is transformed to
'clang-diagnostic-literal-conversion'. However, they need to be enabled by
their original name, e.g. '-e Wliteral-conversion'.

Sometimes GCC is more permissive than Clang, so it is possible that a specific
construction doesn't compile with Clang but compiles with GCC. These
compiler errors are also collected as CodeChecker reports as
'clang-diagnostic-error'.
Note that compiler errors and warnings are captured by CodeChecker only if it
was emitted by clang-tidy.

Checker prefix groups
------------------------------------------------
Checker prefix groups allow you to enable checkers that share a common
prefix in their names. Checkers within a prefix group will have names that
start with the same identifier, making it easier to manage and reference
related checkers.

You can enable/disable checkers belonging to a checker prefix group:
'-e <label>:<value>', e.g. '-e prefix:security'.

Note: The 'prefix' label is mandatory when there is ambiguity between the
name of a checker prefix group and a checker profile or a guideline. This
prevents conflicts and ensures the correct checkers are applied.

See "CodeChecker checkers --help" to learn more.

Checker labels
------------------------------------------------
Each checker is assigned several '<label>:<value>' pairs. For instance,
'cppcheck-deallocret' has the labels 'profile:default' and 'severity:HIGH'. The
goal of labels is that you can enable or disable a batch of checkers with them.

You can enable/disable checkers belonging to a label: '-e <label>:<value>',
e.g. '-e profile:default'.

Note: The 'profile' label is mandatory when there is ambiguity between the
name of a checker profile and a checker prefix group or a guideline. This
prevents conflicts and ensures the correct checkers are applied.

See "CodeChecker checkers --help" to learn more.

Guidelines
------------------------------------------------
CodeChecker recognizes several third party coding guidelines, such as
CppCoreGuidelines, SEI-CERT, or MISRA. These are collections of best
programming practices to avoid common programming errors. Some checkers cover
the rules of these guidelines. CodeChecker assigns the 'guideline' label to
these checkers, such as 'guideline:sei-cert'. This way you can list and enable
those checkers which check the fulfillment of certain guideline rules. See the
output of "CodeChecker checkers --guideline" command.

Guidelines are labels themselves, and can be used as a label:
'-e guideline:<value>', e.g. '-e guideline:sei-cert'.

Note: The 'guideline' label is mandatory when there is ambiguity between the
name of a guideline and a checker prefix group or a checker profile. This
prevents conflicts and ensures the correct checkers are applied.

Batch enabling/disabling checkers
------------------------------------------------
You can fine-tune which checkers to use in the analysis by setting the enable
and disable flags starting from the bigger groups and going inwards. Taking
for example the package hierarchy of 'clangsa', '-e core -d core.uninitialized
-e core.uninitialized.Assign' will enable every 'core' checker, but only
'core.uninitialized.Assign' from the 'core.uninitialized' group. Mind that
disabling certain checkers - such as the 'core' group is unsupported by the
LLVM/Clang community, and thus discouraged.
""")

    checkers_opts.add_argument('-e', '--enable',
                               dest="enable",
                               metavar='checker/group/profile',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker group), "
                                    "profile or guideline "
                                    "to BE USED in the analysis. In case of "
                                    "ambiguity the priority order is profile, "
                                    "guideline, checker name (e.g. security "
                                    "means the profile, not the checker "
                                    "group). Moreover, labels can also be "
                                    "used for selecting checkers, for example "
                                    "profile:extreme or severity:STYLE. See "
                                    "'CodeChecker checkers --label' for "
                                    "further details.")

    checkers_opts.add_argument('-d', '--disable',
                               dest="disable",
                               metavar='checker/group/profile',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker group), "
                                    "profile or guideline "
                                    "to BE PROHIBITED from use in the "
                                    "analysis. In case of "
                                    "ambiguity the priority order is profile, "
                                    "guideline, checker name (e.g. security "
                                    "means the profile, not the checker "
                                    "group). Moreover, labels can also be "
                                    "used for selecting checkers, for example "
                                    "profile:extreme or severity:STYLE. See "
                                    "'CodeChecker checkers --label' for "
                                    "further details.")

    checkers_opts.add_argument('--enable-all',
                               dest="enable_all",
                               action='store_true',
                               required=False,
                               default=argparse.SUPPRESS,
                               help="Force the running analyzers to use "
                                    "almost every checker available. The "
                                    "checker groups 'alpha.', 'debug.',"
                                    "'osx.', 'abseil-', 'android-', "
                                    "'darwin-', 'objc-', "
                                    "'cppcoreguidelines-', 'fuchsia.', "
                                    "'fuchsia-', 'hicpp-', 'llvm-', "
                                    "'llvmlibc-', 'google-', 'zircon-', "
                                    "'osx.' (on Linux) are NOT enabled "
                                    "automatically and must be EXPLICITLY "
                                    "specified. WARNING! Enabling all "
                                    "checkers might result in the analysis "
                                    "losing precision and stability, and "
                                    "could even result in a total failure of "
                                    "the analysis. USE WISELY AND AT YOUR "
                                    "OWN RISK!")

    checkers_opts.add_argument('--disable-all',
                               dest="disable_all",
                               required=False,
                               default=argparse.SUPPRESS,
                               action='store_true',
                               help="Disable all checkers of all analyzers. "
                                    "It is equivalent to using \"--disable "
                                    "default\" as the first argument.")

    checkers_opts.add_argument('--no-missing-checker-error',
                               dest="no_missing_checker_error",
                               action='store_true',
                               required=False,
                               default=argparse.SUPPRESS,
                               help="Emit a warning instead of an error when "
                                    "an unknown checker name is given to "
                                    "either --enable, --disable,"
                                    "--analyzer-config and/or "
                                    "--checker-config.")

    output_opts = parser.add_argument_group("output arguments")

    output_opts.add_argument('--print-steps',
                             dest="print_steps",
                             action="store_true",
                             required=False,
                             default=argparse.SUPPRESS,
                             help="Print the steps the analyzers took in "
                                  "finding the reported defect.")

    output_opts.add_argument('--suppress',
                             type=str,
                             dest="suppress",
                             default=argparse.SUPPRESS,
                             required=False,
                             help="Path of the suppress file to use. Records "
                                  "in the suppress file are used to suppress "
                                  "the display of certain results when "
                                  "parsing the analyses' report. (Reports to "
                                  "an analysis result can also be suppressed "
                                  "in the source code -- please consult the "
                                  "manual on how to do so.) NOTE: The "
                                  "suppress file relies on the "
                                  "\"bug identifier\" generated by the "
                                  "analyzers which is experimental, take "
                                  "care when relying on it.")

    output_opts.add_argument(
        '--trim-path-prefix',
        type=str,
        nargs='*',
        dest="trim_path_prefix",
        required=False,
        default=argparse.SUPPRESS,
        help="Removes leading path from files which will be printed. For "
             "instance if you analyze files '/home/jsmith/my_proj/x.cpp' and "
             "'/home/jsmith/my_proj/y.cpp', but would prefer to have them "
             "displayed as 'my_proj/x.cpp' and 'my_proj/y.cpp' in the web/CLI "
             "interface, invoke CodeChecker with '--trim-path-prefix "
             "\"/home/jsmith/\"'."
             "If multiple prefixes are given, the longest match will be "
             "removed. You may also use Unix shell-like wildcards (e.g. "
             "'/*/jsmith/').")

    parser.add_argument('--review-status',
                        nargs='*',
                        dest="review_status",
                        metavar='REVIEW_STATUS',
                        choices=REVIEW_STATUS_VALUES,
                        default=["confirmed", "unreviewed"],
                        help="Filter results by review statuses. Valid "
                             "values are: {', '.join(REVIEW_STATUS_VALUES)}")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(
        func=main, func_process_config_file=cmd_config.process_config_file)


def main(args):
    """
    Execute a wrapper over log-analyze-parse, aka 'check'.
    """

    logger.setup_logger(args.verbose if 'verbose' in args else None)

    if 'ctu_ast_mode' in args and 'ctu_phases' not in args:
        LOG.error("Analyzer option 'ctu-ast-mode' requires CTU mode enabled")
        sys.exit(1)

    def __update_if_key_exists(source, target, key):
        """Append the source Namespace's element with 'key' to target with
        the same key, but only if it exists."""
        if key in source:
            setattr(target, key, getattr(source, key))

    # If no output directory is given then the checker results go to a
    # temporary directory. This way the subsequent "quick" checks don't pollute
    # the result list of a previous check. If the detection status function is
    # intended to be used (i.e. by keeping the .plist files) then the output
    # directory has to be provided explicitly.
    if 'output_dir' in args:
        output_dir = args.output_dir
    else:
        output_dir = tempfile.mkdtemp()

    output_dir = os.path.abspath(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    logfile = None
    analysis_exit_status = 1  # CodeChecker error.
    try:
        # --- Step 1.: Perform logging if build command was specified.
        if 'command' in args:
            logfile = tempfile.NamedTemporaryFile().name

            # Translate the argument list between check and log.
            log_args = argparse.Namespace(
                command=args.command,
                logfile=logfile
            )
            __update_if_key_exists(args, log_args, 'quiet')
            __update_if_key_exists(args, log_args, 'verbose')

            import codechecker_analyzer.cmd.log as log_module
            LOG.debug("Calling LOG with args:")
            LOG.debug(log_args)

            # If not explicitly given the debug log file of ld_logger is placed
            # in report directory if any. Otherwise parallel "CodeChecker
            # check" commands would overwrite each other's log files under /tmp
            # which is the default location for "CodeChecker check".
            if 'CC_LOGGER_DEBUG_FILE' not in os.environ:
                os.environ['CC_LOGGER_DEBUG_FILE'] = \
                    os.path.join(output_dir, 'codechecker.logger.debug')

            log_module.main(log_args)
        elif 'logfile' in args:
            logfile = args.logfile

        # --- Step 2.: Perform the analysis.
        analyze_args = argparse.Namespace(
            input=logfile,
            output_path=output_dir,
            output_format='plist',
            jobs=args.jobs,
            keep_gcc_include_fixed=args.keep_gcc_include_fixed,
            keep_gcc_intrin=args.keep_gcc_intrin
        )
        # Some arguments don't have default values.
        # We can't set these keys to None because it would result in an error
        # after the call.
        args_to_update = ['quiet',
                          'skipfile',
                          'drop_skipped_reports',
                          'files',
                          'analyzers',
                          'add_compiler_defaults',
                          'cppcheck_args_cfg_file',
                          'clangsa_args_cfg_file',
                          'tidy_args_cfg_file',
                          'analyzer_config',
                          'checker_config',
                          'capture_analysis_output',
                          'generate_reproducer',
                          'config_file',
                          'ctu_ast_mode',
                          'ctu_phases',
                          'ctu_reanalyze_on_failure',
                          'stats_output',
                          'stats_dir',
                          'stats_enabled',
                          'stats_relevance_threshold',
                          'stats_min_sample_count',
                          'enable_all',
                          'disable_all',
                          'no_missing_checker_error',
                          'ordered_checkers',  # --enable and --disable.
                          'timeout',
                          'review_status_config',
                          'compile_uniqueing',
                          'report_hash',
                          'add_gcc_include_dirs_with_isystem',
                          'enable_z3',
                          'enable_z3_refutation']
        for key in args_to_update:
            __update_if_key_exists(args, analyze_args, key)
        if 'clean' in args:
            setattr(analyze_args, 'clean', True)
        __update_if_key_exists(args, analyze_args, 'verbose')
        __update_if_key_exists(args, analyze_args, 'no_missing_checker_error')

        import codechecker_analyzer.cmd.analyze as analyze_module
        LOG.debug("Calling ANALYZE with args:")
        LOG.debug(analyze_args)

        analysis_exit_status = analyze_module.main(analyze_args)

        # --- Step 3.: Print to stdout.
        parse_args = argparse.Namespace(
            input=[output_dir],
            input_format='plist'
        )
        __update_if_key_exists(args, parse_args, 'print_steps')
        __update_if_key_exists(args, parse_args, 'trim_path_prefix')
        __update_if_key_exists(args, parse_args, 'review_status')
        __update_if_key_exists(args, parse_args, 'verbose')
        __update_if_key_exists(args, parse_args, 'skipfile')
        __update_if_key_exists(args, parse_args, 'suppress')

        import codechecker_analyzer.cmd.parse as parse_module
        LOG.debug("Calling PARSE with args:")
        LOG.debug(parse_args)

        parse_module.main(parse_args)
    except ImportError:
        LOG.error("Check failed: couldn't import a library.")
    except Exception:
        LOG.exception("Running check failed.")
        import traceback
        traceback.print_exc()
    finally:
        if 'output_dir' not in args:
            shutil.rmtree(output_dir)
        if 'command' in args:
            os.remove(logfile)

    LOG.debug("Check finished.")

    return analysis_exit_status
