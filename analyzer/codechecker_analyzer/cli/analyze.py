# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Execute analysis over an already existing build.json compilation database.
"""

import argparse
import collections
import json
import os
import shutil
import sys
from typing import List
from pathlib import Path
from functools import partial

from tu_collector import tu_collector

from codechecker_analyzer import analyzer, analyzer_context, \
    compilation_database
from codechecker_analyzer.analyzers import analyzer_types, clangsa
from codechecker_analyzer.arg import \
    OrderedCheckersAction, OrderedConfigAction, existing_abspath, \
    analyzer_config, checker_config, AnalyzerConfigArg, CheckerConfigArg

from codechecker_analyzer.buildlog import log_parser

from codechecker_common import arg, logger, cmd_config, review_status_handler
from codechecker_common.compatibility.multiprocessing import cpu_count
from codechecker_common.skiplist_handler import SkipListHandler, \
    SkipListHandlers
from codechecker_common.util import load_json

LOG = logger.get_logger('system')

header_file_extensions = (
    '.h', '.hh', '.H', '.hp', '.hxx', '.hpp', '.HPP', '.h++', '.tcc')

EPILOG_ENV_VAR = """
  CC_ANALYZERS_FROM_PATH   Set to `yes` or `1` to enforce taking the analyzers
                           from the `PATH` instead of the given binaries.
  CC_ANALYZER_BIN          Set the absolute paths of an analyzer binaries.
                           Overrides other means of CodeChecker getting hold of
                           binary.
                           Format: CC_ANALYZER_BIN='<analyzer1>:/path/to/bin1;
                                                    <analyzer2>:/path/to/bin2'
  CC_CLANGSA_PLUGIN_DIR    If the CC_ANALYZERS_FROM_PATH environment variable
                           is set you can configure the plugin directory of the
                           Clang Static Analyzer by using this environment
                           variable.
"""

EPILOG_ISSUE_HASHES = """
Issue hashes
------------------------------------------------
- By default the issue hash calculation method for 'Clang Static Analyzer' is
context sensitive. It means the hash will be generated based on the following
information:
  * signature of the enclosing function declaration, type declaration or
    namespace.
  * content of the line where the bug is.
  * unique name of the checker.
  * position (column) within the line.

- By default the issue hash calculation method for 'Clang Tidy' is context
insensitive. It means the hash will be generated based on the following
information:
  * 'file name' from the main diag section.
  * 'checker name'.
  * 'checker message'.
  * 'line content' from the source file if can be read up.
  * 'column numbers' from the main diag section.
  * 'range column numbers' only from the control diag sections if column number
    in the range is not the same as the previous control diag section number in
    the bug path. If there are no control sections event section column numbers
    are used.

- context-free: there was a bug and for Clang Tidy the default hash was
generated and not the context free hash (kept for backward compatibility). Use
'context-free-v2' instead of this.

- context-free-v2:
  * 'file name' from the main diag section.
  * 'checker message'.
  * 'line content' from the source file if can be read up. All the whitespaces
    from the source content are removed.
  * 'column numbers' from the main diag sections location.

- diagnostic-message:
  * Same as 'context-free-v2' (file name, checker message etc.)
  * 'bug step messages' from all events.

  Be careful with this hash because it can change easily for example on
  variable / function renames.

OUR RECOMMENDATION: we recommend you to use 'context-free-v2' hash because the
hash will not be changed so easily for example on code indentation or when a
checker is renamed.

For more information see:
https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/report_identification.md
"""

EPILOG_EXIT_STATUS = """
Exit status
------------------------------------------------
0 - Successful analysis
1 - CodeChecker error
3 - Analysis of at least one translation unit failed
128+signum - Terminating on a fatal signal whose number is signum
"""


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """
    return {
        'prog': 'CodeChecker analyze',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': """
Use the previously created JSON Compilation Database to perform an analysis on
the project, outputting analysis results in a machine-readable format.""",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': f"""
Environment variables
------------------------------------------------
{EPILOG_ENV_VAR}

{EPILOG_ISSUE_HASHES}

{EPILOG_EXIT_STATUS}

Compilation databases can be created by instrumenting your project's build via
'CodeChecker log'. To transform the results of the analysis to a human-friendly
format, please see the commands 'CodeChecker parse' or 'CodeChecker store'.
""",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Execute the supported code analyzers for the files "
                "recorded in a JSON Compilation Database."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('input',
                        type=existing_abspath,
                        help="The input of the analysis can be either a "
                             "compilation database JSON file, a path to a "
                             "source file or a path to a directory containing "
                             "source files.")

    parser.add_argument('-j', '--jobs',
                        type=int,
                        dest="jobs",
                        required=False,
                        default=cpu_count(),
                        help="Number of threads to use in analysis. More "
                             "threads mean faster analysis at the cost of "
                             "using more memory.")

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

    parser.add_argument('--review-status-config',
                        dest="review_status_config",
                        required=False,
                        type=existing_abspath,
                        default=argparse.SUPPRESS,
                        help="Path of review_status.yaml config file which "
                             "contains review status settings assigned to "
                             "specific directories, checkers, bug hashes.")

    parser.add_argument('-o', '--output',
                        dest="output_path",
                        required=True,
                        default=argparse.SUPPRESS,
                        help="Store the analysis output in the given folder.")

    parser.add_argument('--compiler-info-file',
                        dest="compiler_info_file",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Read the compiler includes and target from the "
                             "specified file rather than invoke the compiler "
                             "executable.")

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

    parser.add_argument('-t', '--type', '--output-format',
                        dest="output_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results should "
                             "use.")

    parser.add_argument('--makefile',
                        dest="makefile",
                        required=False,
                        action='store_true',
                        default=False,
                        help="Generate a Makefile in the given output "
                             "directory from the analyzer commands and do not "
                             "execute the analysis. The analysis can be "
                             "executed by calling the make command like "
                             "'make -f output_dir/Makefile'. You can ignore "
                             "errors with the -i/--ignore-errors options: "
                             "'make -f output_dir/Makefile -i'.")

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

    parser.add_argument('--report-hash',
                        dest="report_hash",
                        default=argparse.SUPPRESS,
                        required=False,
                        choices=[
                            'context-free',
                            'context-free-v2',
                            'diagnostic-message'],
                        help="R|Specify the hash calculation method for "
                             "reports. By default the calculation method for "
                             "Clang Static Analyzer is context sensitive and "
                             "for Clang Tidy it is context insensitive.\n"
                             "You can use the following calculation methods:\n"
                             "- context-free: there was a bug and for Clang "
                             "Tidy not the context free hash was generated "
                             "(kept for backward compatibility).\n"
                             "- context-free-v2: context free hash is used "
                             "for ClangSA and Clang Tidy.\n"
                             "- diagnostic-message: context free hash with "
                             "bug step messages is used for ClangSA and "
                             "Clang Tidy.\n"
                             "See the 'issue hashes' section of the help "
                             "message of this command below for more "
                             "information.\n"
                             "USE WISELY AND AT YOUR OWN RISK!")

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

    analyzer_opts.add_argument('--cppcheckargs',
                               dest="cppcheck_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="DEPRECATED. "
                                    "File containing argument which will be "
                                    "forwarded verbatim for Cppcheck. The "
                                    "option has been migrated under the "
                                    "cppcheck anayzer options: "
                                    "--analyzer-config "
                                    "cppcheck:cc-verbatim-args-file="
                                    "<filepath>")

    analyzer_opts.add_argument('--saargs',
                               dest="clangsa_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="DEPRECATED. "
                                    "File containing argument which will be "
                                    "forwarded verbatim for the Clang Static "
                                    "Analyzer. The opion has been migrated "
                                    "under the clangsa analyzer options: "
                                    "--analyzer-config "
                                    "clangsa:cc-verbatim-args-file=<filepath>")

    analyzer_opts.add_argument('--tidyargs',
                               dest="tidy_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="DEPRECATED. "
                                    "File containing argument which will be "
                                    "forwarded verbatim for Clang-Tidy. "
                                    "The opion has been migrated under the "
                                    "clang-tidy analyzer options: "
                                    "--analyzer-config "
                                    "clang-tidy:cc-verbatim-args-file="
                                    "<filepath>")

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
                               default=[],
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

    # Only check for AST loading modes if CTU is available.
    ctu_opts.add_argument('--ctu-ast-mode',
                          action='store',
                          dest='ctu_ast_mode',
                          choices=['load-from-pch', 'parse-on-demand'],
                          default=argparse.SUPPRESS,
                          help="Choose the way ASTs are loaded during "
                               "CTU analysis. Mode 'load-from-pch' "
                               "generates PCH format serialized ASTs "
                               "during the 'collect' phase. Mode "
                               "'parse-on-demand' only generates the "
                               "invocations needed to parse the ASTs. "
                               "Mode 'load-from-pch' can use "
                               "significant disk-space for the "
                               "serialized ASTs, while mode "
                               "'parse-on-demand' can incur some "
                               "runtime CPU overhead in the second "
                               "phase of the analysis. NOTE: Only "
                               "available if CTU mode is enabled. "
                               "(default: parse-on-demand)")

    stats_capable = analyzer_types.is_statistics_capable()

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
                           action="store_true",
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
                           default="10" if stats_capable
                                   else argparse.SUPPRESS,
                           type=int,
                           dest='stats_min_sample_count',
                           help="Minimum number of samples (function call"
                                " occurrences) to be collected"
                                " for a statistics to be relevant "
                                "'<MIN-SAMPLE-COUNT>'.")

    stat_opts.add_argument('--stats-relevance-threshold',
                           action='store',
                           default="0.85" if stats_capable
                                   else argparse.SUPPRESS,
                           type=float,
                           dest='stats_relevance_threshold',
                           help="The minimum ratio of calls of function "
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
                               help="Set a checker (or checker prefix group), "
                                    "profile or guideline to BE USED in the "
                                    "analysis. Labels can also be "
                                    "used for selecting checkers, for example "
                                    "profile:extreme or severity:STYLE. See "
                                    "'CodeChecker checkers --label' for "
                                    "further details. In case of a name clash "
                                    "between the checker prefix "
                                    "group/profile/guideline name, the use of "
                                    "one of the following labels is "
                                    "mandatory: 'checker:', 'prefix:', "
                                    "'profile:', 'guideline:'. If a checker "
                                    "name matches multiple checkers as a "
                                    "prefix, 'checker:' or 'prefix:' "
                                    "namespace is required")

    checkers_opts.add_argument('-d', '--disable',
                               dest="disable",
                               metavar='checker/group/profile',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker prefix group), "
                                    "profile or guideline "
                                    "to BE PROHIBITED from use in the "
                                    "analysis. Labels can also be "
                                    "used for selecting checkers, for example "
                                    "profile:extreme or severity:STYLE. See "
                                    "'CodeChecker checkers --label' for "
                                    "further details. In case of a name clash "
                                    "between the checker prefix "
                                    "group/profile/guideline name, the use of "
                                    "one of the following labels is "
                                    "mandatory: 'checker:', 'prefix:', "
                                    "'profile:', 'guideline:'. If a checker "
                                    "name matches multiple checkers as a "
                                    "prefix, 'checker:' or 'prefix:' "
                                    "namespace is required")

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

    logger.add_verbose_arguments(parser)
    parser.set_defaults(
        func=main, func_process_config_file=cmd_config.process_config_file)


def is_analyzer_config_valid(
    args,
    analyzer_config_args: List[AnalyzerConfigArg]
) -> bool:
    """
    Ensure that the analyzer_config parameter is set to a valid value
    by verifying if it belongs to the set of allowed values.
    """
    wrong_config_messages = []
    available_analyzers = {}

    for analyzer_name, analyzer_class in \
            analyzer_types.supported_analyzers.items():
        if analyzer_class.get_binary_version() is not None:
            available_analyzers[analyzer_name] = analyzer_class

    enabled_analyzers = {}
    if args.analyzers:
        enabled_analyzer_names = \
            set(args.analyzers).intersection(available_analyzers)
        enabled_analyzers = {
            analyzer_name: available_analyzers[analyzer_name]
            for analyzer_name in enabled_analyzer_names
        }

    if enabled_analyzers:
        available_analyzers = enabled_analyzers

    analyzer_configs = {}
    for analyzer_name, analyzer_class in available_analyzers.items():
        try:
            analyzer_configs[analyzer_name] = \
                analyzer_class.get_analyzer_config()
        except Exception as e:
            wrong_config_messages.append(
                f"Could not get config for analyzer '{analyzer_name}'. "
                f"Error: {e}")
            continue

    for cfg_arg in analyzer_config_args:
        if cfg_arg.analyzer not in available_analyzers:
            wrong_config_messages.append(
                f"Invalid argument to --analyzer-config: '{cfg_arg.analyzer}' "
                f"is not an available analyzer. Available analyzers are: "
                f"{', '.join(a for a in available_analyzers)}.")
            continue

        if enabled_analyzers and cfg_arg.analyzer not in enabled_analyzers:
            continue

        try:
            analyzer_cfg = next(
                (x for x in analyzer_configs[cfg_arg.analyzer]
                 if x.option == cfg_arg.option),
                None)
        except Exception:
            wrong_config_messages.append(
                f"The analyzer '{cfg_arg.analyzer}' is not found! Make sure "
                "it is loaded or exists with the command "
                "'CodeChecker analyzers'"
            )
            continue

        if analyzer_cfg is None:
            wrong_config_messages.append(
                f"Invalid argument to --analyzer-config: {cfg_arg.analyzer} "
                f"has no config named '{cfg_arg.option}'. Use the "
                f"'CodeChecker analyzers --analyzer-config "
                f"{cfg_arg.analyzer}' command to see available configs.")
        else:
            try:
                analyzer_cfg.value_type(cfg_arg.value)
            except Exception as ex:
                wrong_config_messages.append(
                    f"Invalid value to --analyzer-config: "
                    f"'{cfg_arg.analyzer}:{cfg_arg.option}={cfg_arg.value}'. "
                    f"{ex}")

    if wrong_config_messages:
        for wrong_config_message in wrong_config_messages:
            LOG.error(wrong_config_message)

        return False

    return True


def is_checker_config_valid(
    checker_config_args: List[CheckerConfigArg]
) -> bool:
    """
    Ensure that the checker_config parameter is set to a valid value
    by verifying if it belongs to the set of allowed values.
    """
    wrong_config_messages = []
    supported_analyzers = analyzer_types.supported_analyzers

    checker_configs = {
        analyzer_name: analyzer_class.get_checker_config()
        for analyzer_name, analyzer_class
        in supported_analyzers.items()
    }

    for cfg_arg in checker_config_args:
        if cfg_arg.analyzer not in supported_analyzers:
            wrong_config_messages.append(
                f"Invalid argument to --checker-config: '{cfg_arg.analyzer}' "
                f"is not a supported analyzer. Supported analyzers are: "
                f"{', '.join(a for a in supported_analyzers)}.")
            continue

        checker_cfg = next(
            (x for x in checker_configs[cfg_arg.analyzer]
             if x.checker == cfg_arg.checker and x.option == cfg_arg.option),
            None)

        if checker_cfg is None:
            wrong_config_messages.append(
                f"Invalid argument to --checker-config: invalid checker "
                f"'{cfg_arg.checker}' and/or checker option "
                f"'{cfg_arg.option}' for {cfg_arg.analyzer}. Use the "
                f"'CodeChecker checkers --checker-config' command to see "
                f"available checker options.")

    if wrong_config_messages:
        for wrong_config_message in wrong_config_messages:
            LOG.error(wrong_config_message)

        return False

    return True


def get_affected_file_paths(
    file_filters: List[str],
    compile_commands: tu_collector.CompilationDB
) -> List[str]:
    """
    Returns a list of source files for existing header file otherwise returns
    with the same file path expression.
    """
    file_paths = []  # Use list to keep the order of the file paths.
    for file_filter in file_filters:
        file_paths.append(str(Path(file_filter).resolve())
                          if '*' not in file_filter else file_filter)

        if os.path.exists(file_filter) and \
                file_filter.endswith(header_file_extensions):
            LOG.info("Get dependent source files for '%s'...", file_filter)
            dependent_sources = tu_collector.get_dependent_sources(
                compile_commands, file_filter)

            LOG.info("Get dependent source files for '%s' done.", file_filter)
            LOG.debug("Dependent source files: %s",
                      ', '.join(dependent_sources))

            file_paths.extend(dependent_sources)

    return file_paths


def __get_skip_handlers(args, compile_commands) -> SkipListHandlers:
    """
    Initialize and return a list of skiplist handlers if
    there is a skip list file in the arguments or files options is provided.
    """
    skip_handlers = SkipListHandlers()
    if 'files' in args:
        source_file_paths = get_affected_file_paths(
            args.files, compile_commands)

        # Creates a skip file where all source files will be skipped except
        # the given source files and all the header files.
        skip_files = [f'+{f}' for f in source_file_paths]
        skip_files.extend(['+/*.h', '+/*.H', '+/*.tcc'])
        skip_files.append('-*')
        content = "\n".join(skip_files)
        skip_handlers.append(SkipListHandler(content))
        LOG.debug("Skip handler is created for the '--file' option with the "
                  "following filters:\n%s", content)
    if 'skipfile' in args:
        with open(args.skipfile, encoding="utf-8", errors="ignore") as f:
            content = f.read()
            skip_handlers.append(SkipListHandler(content))
            LOG.debug("Skip handler is created for the '--ignore' option with "
                      "the following filters:\n%s", content)

    return skip_handlers


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


def __update_review_status_config(args):
    rs_config_to_send = os.path.join(args.output_path, 'review_status.yaml')

    if os.path.exists(rs_config_to_send):
        os.remove(rs_config_to_send)

    if 'review_status_config' in args:
        LOG.debug("Copying review status config file %s to %s",
                  args.review_status_config, rs_config_to_send)
        os.symlink(args.review_status_config, rs_config_to_send)


def __cleanup_metadata(metadata_prev, metadata):
    """ Cleanup metadata.

    If the source file for a plist does not exist, remove the plist from the
    system and from the metadata.
    """
    if not metadata_prev:
        return

    result_src_files = __get_result_source_files(metadata_prev)
    for plist_file, source_file in result_src_files.items():
        if not os.path.exists(source_file):
            try:
                LOG.info("Remove plist file '%s' because it refers to a "
                         "source file ('%s') which was removed.",
                         plist_file, source_file)
                __del_result_source_file(metadata, plist_file)
                os.remove(plist_file)
            except OSError:
                LOG.warning("Failed to remove plist file: %s", plist_file)


def __del_result_source_file(metadata, file_path):
    """ Remove file path from metadata result source files. """
    if 'result_source_files' in metadata:
        # Kept for backward-compatibility reason.
        del metadata['result_source_files'][file_path]
    else:
        for tool in metadata.get('tools', {}):
            result_source_files = tool.get('result_source_files', {})
            del result_source_files[file_path]


def __get_result_source_files(metadata):
    """ Get result source files from the given metadata. """
    if 'result_source_files' in metadata:
        return metadata['result_source_files']

    result_src_files = {}
    for tool in metadata.get('tools', {}):
        r_src_files = tool.get('result_source_files', {})
        result_src_files.update(r_src_files.items())

    return result_src_files


def __transform_deprecated_flags(args):
    """
    There are some deprecated flags among the command line arguments that have
    another way of usage. In this function we do this transformation so the old
    flags are still functioning until they are competely removed in some future
    version.
    """
    if hasattr(args, 'clangsa_args_cfg_file'):
        args.analyzer_config.append(analyzer_config(
            f'clangsa:cc-verbatim-args-file={args.clangsa_args_cfg_file}'))
        delattr(args, 'clangsa_args_cfg_file')
        LOG.warning(
            '"--saargs" is deprecated. Use "--analyzer-config '
            'clangsa:cc-verbatim-args-file=<filepath>" instead.')
    if hasattr(args, 'tidy_args_cfg_file'):
        args.analyzer_config.append(analyzer_config(
            f'clang-tidy:cc-verbatim-args-file={args.tidy_args_cfg_file}'))
        delattr(args, 'tidy_args_cfg_file')
        LOG.warning(
            '"--tidyargs" is deprecated. Use "--analyzer-config '
            'clang-tidy:cc-verbatim-args-file=<filepath>" instead.')
    if hasattr(args, 'cppcheck_args_cfg_file'):
        args.analyzer_config.append(analyzer_config(
            f'clang-tidy:cc-verbatim-args-file={args.cppcheck_args_cfg_file}'))
        delattr(args, 'cppcheck_args_cfg_file')
        LOG.warning(
            '"--cppcheckargs" is deprecated. Use "--analyzer-config '
            'cppcheck:cc-verbatim-args-file=<filepath>" instead.')


def check_satisfied_capabilities(args):
    has_error = False
    for attr in dir(args):
        # NOTE: This is a heuristic: there are many arguments for statistics
        # and for ctu, but conveniently, all of them store to stats* or ctu*
        # names fields of args. Lets exploit that instead of manually listing
        # args.
        if attr.startswith("stats") and not \
                analyzer_types.is_statistics_capable():
            LOG.error("Statistics options can only be enabled if clang has "
                      "statistics checkers available!")
            LOG.info("CodeChecker has not found Clang Static Analyzer "
                     "checkers statisticsCollector.ReturnValueCheck and "
                     "statisticsCollector.SpecialReturnValue")
            has_error = True
            break
        if attr.startswith("ctu") and not \
                analyzer_types.is_ctu_capable():
            LOG.error("CrossTranslation Unit options can only be enabled if "
                      "clang itself supports it!")
            LOG.info("hint: Clang 8.0.0 is the earliest version to support it")
            has_error = True
            break

    if 'ctu_ast_mode' in args and not \
            analyzer_types.is_ctu_on_demand_available():
        LOG.error("Clang does not support on-demand Cross Translation Unit"
                  "analysis!")
        LOG.info("hint: Clang 11.0.0 is the earliest version to support it")
        has_error = True

    if 'enable_z3' in args and args.enable_z3 == 'on' and not \
            analyzer_types.is_z3_capable():
        LOG.error("Z3 solver cannot be enabled as Clang was not compiled with "
                  "Z3!")
        has_error = True

    if 'enable_z3_refutation' in args and args.enable_z3_refutation == 'on' \
            and not analyzer_types.is_z3_capable():
        LOG.error("Z3 refutation cannot be enabled as Clang was not compiled "
                  "with Z3!")
        has_error = True

    if has_error:
        LOG.info("hint: Maybe CodeChecker found the wrong analyzer binary?")
        sys.exit(1)


def main(args):
    """
    Perform analysis on the given inputs. Possible inputs are a compilation
    database, a source file or the path of a project. The analysis results are
    stored to a report directory given by -o flag.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

    __transform_deprecated_flags(args)

    # Validate analyzer and checker config (if any)
    config_validator = {
        'analyzer_config': partial(is_analyzer_config_valid, args),
        'checker_config': is_checker_config_valid
    }

    config_validator_res = [validate_func(getattr(args, conf))
                            for conf, validate_func in config_validator.items()
                            if conf in args]

    if False in config_validator_res \
            and 'no_missing_checker_error' not in args:
        LOG.info("Although it is not recommended, if you want to suppress "
                 "errors relating to unknown analyzer/checker configs, "
                 "consider using the option '--no-missing-checker-error'")
        sys.exit(1)

    if 'tidy_config' in args:
        LOG.warning(
            "--tidy-config is deprecated and will be removed in the next "
            "release. Use --analyzer-config or --checker-config instead.")

    # CTU loading mode is only meaningful if CTU itself is enabled.
    if 'ctu_ast_mode' in args and 'ctu_phases' not in args:
        LOG.error("Analyzer option 'ctu-ast-mode' requires CTU mode enabled")
        sys.exit(1)

    check_satisfied_capabilities(args)

    try:
        cmd_config.check_config_file(args)
    except FileNotFoundError as fnerr:
        LOG.error(fnerr)
        sys.exit(1)

    args.output_path = os.path.abspath(args.output_path)
    if os.path.exists(args.output_path) and \
            not os.path.isdir(args.output_path):
        LOG.error("The given output path is not a directory: " +
                  args.output_path)
        sys.exit(1)

    if 'enable_all' in args:
        LOG.info("'--enable-all' was supplied for this analysis.")
    if 'disable_all' in args:
        if 'ordered_checkers' not in args:
            args.ordered_checkers = []
        args.ordered_checkers.insert(0, ('default', False))

    # Enable alpha uniqueing by default if ctu analysis is used.
    if 'none' in args.compile_uniqueing and 'ctu_phases' in args:
        args.compile_uniqueing = "alpha"

    compiler_info_file = None
    if 'compiler_info_file' in args:
        LOG.debug("Compiler info is read from: %s", args.compiler_info_file)
        if not os.path.exists(args.compiler_info_file):
            LOG.error("Compiler info file %s does not exist",
                      args.compiler_info_file)
            sys.exit(1)
        compiler_info_file = args.compiler_info_file

    compile_commands = \
        compilation_database.gather_compilation_database(args.input)
    if compile_commands is None:
        LOG.error(f"Found no compilation commands in '{args.input}'")
        sys.exit(1)

    # Process the skip list if present. This will filter out analysis actions.
    skip_handlers = __get_skip_handlers(args, compile_commands)
    # Post processin filters
    filter_handlers = None
    if ('drop_skipped_reports' in args and args.drop_skipped_reports):
        filter_handlers = skip_handlers

    rs_handler = review_status_handler.ReviewStatusHandler(args.output_path)

    try:
        if 'review_status_config' in args:
            rs_handler.set_review_status_config(args.review_status_config)
    except ValueError as ex:
        LOG.error(ex)
        sys.exit(1)

    ctu_or_stats_enabled = False
    # Skip list is applied only in pre-analysis
    # if --ctu-collect was called explicitly.
    pre_analysis_skip_handlers = None
    if 'ctu_phases' in args:
        ctu_collect = args.ctu_phases[0]
        ctu_analyze = args.ctu_phases[1]
        if ctu_collect and not ctu_analyze:
            pre_analysis_skip_handlers = skip_handlers

        if ctu_collect or ctu_analyze:
            ctu_or_stats_enabled = True

    # Skip list is applied only in pre-analysis
    # if --stats-collect was called explicitly.
    if 'stats_output' in args and args.stats_output:
        pre_analysis_skip_handlers = skip_handlers
        ctu_or_stats_enabled = True

    if 'stats_enabled' in args and args.stats_enabled:
        ctu_or_stats_enabled = True

    context = analyzer_context.get_context()

    # Number of all the compilation commands in the parsed log files,
    # logged by the logger.
    all_cmp_cmd_count = len(compile_commands)

    # We clear the output directory in the following cases.
    ctu_dir = os.path.join(args.output_path, 'ctu-dir')
    if 'ctu_phases' in args and args.ctu_phases[0] and \
            os.path.isdir(ctu_dir):
        # Clear the CTU-dir if the user turned on the collection phase.
        LOG.debug("Previous CTU contents have been deleted.")
        shutil.rmtree(ctu_dir)

    if 'clean' in args and os.path.isdir(args.output_path):
        LOG.info("Previous analysis results in '%s' have been removed, "
                 "overwriting with current result", args.output_path)
        shutil.rmtree(args.output_path)

    if not os.path.exists(args.output_path):
        os.makedirs(args.output_path)

    # TODO: I'm not sure that this directory should be created here.
    fixit_dir = os.path.join(args.output_path, 'fixit')
    if not os.path.exists(fixit_dir):
        os.makedirs(fixit_dir)

    LOG.debug("args: %s", str(args))
    LOG.debug("Output will be stored to: '%s'", args.output_path)

    analyzer_clang_binary = \
        context.analyzer_binaries.get(
            clangsa.analyzer.ClangSA.ANALYZER_NAME)

    analyzer_clang_version = None
    if analyzer_clang_binary:
        analyzer_clang_version = clangsa.version.get(analyzer_clang_binary)

    actions, skipped_cmp_cmd_count = log_parser.parse_unique_log(
        compile_commands,
        args.output_path,
        args.compile_uniqueing,
        compiler_info_file,
        args.keep_gcc_include_fixed,
        args.keep_gcc_intrin,
        args.jobs,
        skip_handlers,
        pre_analysis_skip_handlers,
        ctu_or_stats_enabled,
        analyzer_clang_version)

    if not actions:
        LOG.warning("No analysis is required.")
        LOG.warning("There were no compilation commands in the provided "
                    "compilation database or all of them were skipped.")
        sys.exit(0)

    uniqued_compilation_db_file = os.path.join(
        args.output_path, "unique_compile_commands.json")
    with open(uniqued_compilation_db_file, 'w',
              encoding="utf-8", errors="ignore") as f:
        json.dump(actions, f,
                  cls=log_parser.CompileCommandEncoder)

    metadata = {
        'version': 2,
        'tools': [{
            'name': 'codechecker',
            'action_num': len(actions),
            'command': sys.argv,
            'version':
            f"{context.package_git_tag} ({context.package_git_hash})",
            'working_directory': os.getcwd(),
            'output_path': args.output_path,
            'result_source_files': {},
            'analyzers': {}
        }]}
    metadata_tool = metadata['tools'][0]

    if 'name' in args:
        metadata_tool['run_name'] = args.name

    # Update metadata dictionary with old values.
    metadata_file = os.path.join(args.output_path, 'metadata.json')
    metadata_prev = None
    if os.path.exists(metadata_file):
        metadata_prev = load_json(metadata_file)
        metadata_tool['result_source_files'] = \
            __get_result_source_files(metadata_prev)

    CompileCmdParseCount = \
        collections.namedtuple('CompileCmdParseCount',
                               'total, analyze, skipped, removed_by_uniqueing')
    cmp_cmd_to_be_uniqued = all_cmp_cmd_count - skipped_cmp_cmd_count

    # Number of compile commands removed during uniqueing.
    removed_during_uniqueing = cmp_cmd_to_be_uniqued - len(actions)

    all_to_be_analyzed = cmp_cmd_to_be_uniqued - removed_during_uniqueing

    compile_cmd_count = CompileCmdParseCount(
        total=all_cmp_cmd_count,
        analyze=all_to_be_analyzed,
        skipped=skipped_cmp_cmd_count,
        removed_by_uniqueing=removed_during_uniqueing)

    LOG.debug("Total number of compile commands without "
              "skipping or uniqueing: %d", compile_cmd_count.total)
    LOG.debug("Compile commands removed by uniqueing: %d",
              compile_cmd_count.removed_by_uniqueing)
    LOG.debug("Compile commands skipped during log processing: %d",
              compile_cmd_count.skipped)
    LOG.debug("Compile commands forwarded for analysis: %d",
              compile_cmd_count.analyze)

    analyzer.perform_analysis(args, skip_handlers, filter_handlers,
                              rs_handler, actions, metadata_tool,
                              compile_cmd_count)

    __update_skip_file(args)
    __update_review_status_config(args)

    LOG.debug("Cleanup metadata file started.")
    __cleanup_metadata(metadata_prev, metadata)
    LOG.debug("Cleanup metadata file finished.")

    LOG.debug("Analysis metadata write to '%s'", metadata_file)
    with open(metadata_file, 'w',
              encoding="utf-8", errors="ignore") as metafile:
        json.dump(metadata, metafile)

    # WARN: store command will search for this file!!!!
    compile_cmd_json = os.path.join(args.output_path, 'compile_cmd.json')
    with open(compile_cmd_json, 'w', encoding="utf-8", errors="ignore") as f:
        json.dump(compile_commands, f, indent=2)

    try:
        # pylint: disable=no-name-in-module
        from codechecker_analyzer import analyzer_statistics
        LOG.debug("Sending analyzer statistics started.")
        analyzer_statistics.collect(metadata, "analyze")
        LOG.debug("Sending analyzer statistics finished.")
    except Exception:
        LOG.debug("Failed to send analyzer statistics!")

    # Generally exit status is set by sys.exit() call in CodeChecker. However,
    # exit code 3 has a special meaning: it returns when the underlying
    # analyzer tool fails.
    # "CodeChecker analyze" is special in the sense that it can be invoked
    # either top-level or through "CodeChecker check". In the latter case
    # "CodeChecker check" should have the same exit status. Calling sys.exit()
    # at this specific point is not an option, because the remaining statements
    # of "CodeChecker check" after the analysis wouldn't execute.
    for analyzer_data in metadata_tool['analyzers'].values():
        if analyzer_data['analyzer_statistics']['failed'] != 0:
            return 3

    return 0
