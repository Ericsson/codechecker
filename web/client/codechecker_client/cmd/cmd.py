# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
The CodeChechecker command-line client can be used to view information about
analysis reports found on a running viewer 'server' from a command-line.
"""


import argparse
import getpass
import datetime
import sys

from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from codechecker_client import cmd_line_client
from codechecker_client import product_client
from codechecker_client import permission_client, source_component_client, \
    token_client

from codechecker_common import arg, logger, util
from codechecker_common.output import USER_FORMATS

DEFAULT_FILTER_VALUES = {
    'review_status': ['unreviewed', 'confirmed'],
    'detection_status': ['new', 'reopened', 'unresolved'],
    'uniqueing': 'off'
}

DEFAULT_OUTPUT_FORMATS = ["plaintext"] + USER_FORMATS


def valid_time(t):
    """
    Constructs a datetime from a 'year:month:day:hour:minute:second'-formatted
    string.
    """

    try:
        parts = list(map(int, t.split(':')))
        parts = parts + [0] * (6 - len(parts))
        year, month, day, hour, minute, second = parts
        return datetime.datetime(year, month, day, hour, minute, second)
    except ValueError as ex:
        raise argparse.ArgumentTypeError(ex)


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker cmd',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "The command-line client is used to connect to a "
                       "running 'CodeChecker server' (either remote or "
                       "local) and quickly inspect analysis results, such as "
                       "runs, individual defect reports, compare analyses, "
                       "etc. Please see the invidual subcommands for further "
                       "details.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "View analysis results on a running server from the "
                "command line.",
    }


def __add_output_formats(parser, output_formats=None,
                         allow_multiple_outputs=False,
                         help_msg=None):
    """ Add output arguments to the given parser. """
    if not output_formats:
        # Use default output formats.
        output_formats = DEFAULT_OUTPUT_FORMATS

    if not help_msg:
        help_msg = "The output format(s) to use in showing the data."

    if allow_multiple_outputs:
        parser.add_argument('-o', '--output',
                            nargs="+",
                            dest="output_format",
                            required=False,
                            default=["plaintext"],
                            choices=output_formats,
                            help=help_msg)
    else:
        parser.add_argument('-o', '--output',
                            dest="output_format",
                            required=False,
                            default="plaintext",
                            choices=output_formats,
                            help=help_msg)

    output_requires_export_dir = ["html", "gerrit", "codeclimate"]
    if any(out_f in output_requires_export_dir for out_f in output_formats):
        parser.add_argument('-e', '--export-dir',
                            dest="export_dir",
                            default=argparse.SUPPRESS,
                            help="Store the output in the given folder.")

        parser.add_argument('-c', '--clean',
                            dest="clean",
                            required=False,
                            action='store_true',
                            default=argparse.SUPPRESS,
                            help="Delete output results stored in the output "
                                 "directory. (By default, it would keep "
                                 "output files and overwrites only those "
                                 "that contain any reports).")


def __add_url_arguments(parser, needs_product_url=True):
    """ Add product url arguments to the given parser. """
    if needs_product_url is None:
        # Explicitly not add anything, the command does not connect to a
        # server.
        pass
    elif needs_product_url:
        # Command connects to a product on a server.
        parser.add_argument('--url',
                            type=str,
                            metavar='PRODUCT_URL',
                            dest="product_url",
                            default="localhost:8001/Default",
                            required=False,
                            help="The URL of the product which will be "
                                 "accessed by the client, in the format of "
                                 "'[http[s]://]host:port/Endpoint'.")
    else:
        # Command connects to a server directly.
        parser.add_argument('--url',
                            type=str,
                            metavar='SERVER_URL',
                            dest="server_url",
                            default="localhost:8001",
                            required=False,
                            help="The URL of the server to access, in the "
                                 "format of '[http[s]://]host:port'.")


def __add_common_arguments(parser,
                           needs_product_url=True,
                           output_formats=None,
                           output_help_message=None,
                           allow_multiple_outputs=False):
    """
    Add some common arguments, like server address and verbosity, to parser.
    """

    common_group = parser.add_argument_group('common arguments')
    __add_url_arguments(common_group, needs_product_url)

    if output_formats:
        __add_output_formats(parser, output_formats, allow_multiple_outputs,
                             output_help_message)

    logger.add_verbose_arguments(common_group)


def __add_filtering_arguments(parser, defaults=None, diff_mode=False):
    """
    Add some common filtering arguments to the given parser.
    """

    def init_default(dest):
        return defaults[dest] if defaults and dest in defaults \
            else argparse.SUPPRESS

    f_group = parser.add_argument_group('filter arguments')

    warn_diff_mode = ""
    if diff_mode:
        warn_diff_mode = " This can be used only if basename or newname is " \
                         "a run name (on the remote server)."

    f_group.add_argument('--uniqueing',
                         dest="uniqueing",
                         required=False,
                         default=init_default('uniqueing'),
                         choices=['on', 'off'],
                         help="The same bug may appear several times if it is "
                              "found on different execution paths, i.e. "
                              "through different function calls. By turning "
                              "on uniqueing a report appears only once even "
                              "if it is found on several paths.")

    f_group.add_argument('--report-hash',
                         nargs='*',
                         dest="report_hash",
                         metavar='REPORT_HASH',
                         default=init_default('report_hash'),
                         help="Filter results by report hashes.")

    f_group.add_argument('--review-status',
                         nargs='*',
                         dest="review_status",
                         metavar='REVIEW_STATUS',
                         default=init_default('review_status'),
                         help="R|Filter results by review statuses.\n"
                              "Reports can be assigned a review status of the "
                              "following values:\n"
                              "- Unreviewed: Nobody has seen this report.\n"
                              "- Confirmed: This is really a bug.\n"
                              "- False positive: This is not a bug.\n"
                              "- Intentional: This report is a bug but we "
                              "don't want to fix it." +
                              warn_diff_mode)

    f_group.add_argument('--detection-status',
                         nargs='*',
                         dest="detection_status",
                         metavar='DETECTION_STATUS',
                         default=init_default('detection_status'),
                         help="R|Filter results by detection statuses.\n"
                              "The detection status is the latest state of a "
                              "bug report in a run. When a unique report is "
                              "first detected it will be marked as New. When "
                              "the report is stored again with the same run "
                              "name then the detection status changes to one "
                              "of the following options:\n"
                              "- Resolved: when the bug report can't be found "
                              "after the subsequent storage.\n"
                              "- Unresolved: when the bug report is still "
                              "among the results after the subsequent "
                              "storage.\n"
                              "- Reopened: when a Resolved bug appears "
                              "again.\n"
                              "- Off: The bug was reported by a checker that "
                              "was switched off during the last analysis "
                              "which results were stored.\n"
                              "- Unavailable: were reported by a checker that "
                              "does not exists in the analyzer anymore "
                              "because it was removed or renamed." +
                              warn_diff_mode)

    f_group.add_argument('--severity',
                         nargs='*',
                         dest="severity",
                         metavar='SEVERITY',
                         default=init_default('severity'),
                         help="Filter results by severities.")

    f_group.add_argument('--bug-path-length',
                         type=str,
                         dest='bug_path_length',
                         default=argparse.SUPPRESS,
                         help="Filter results by bug path length. This has "
                              "the following format: <minimum_bug_path_length>"
                              ":<maximum_bug_path_length>. Valid values are: "
                              "\"4:10\", \"4:\", \":10\"")

    f_group.add_argument('--tag',
                         nargs='*',
                         dest="tag",
                         metavar='TAG',
                         default=init_default('tag'),
                         help="Filter results by version tag names." +
                         warn_diff_mode)

    f_group.add_argument('--outstanding-reports-date', '--open-reports-date',
                         type=valid_time,
                         dest="open_reports_date",
                         metavar='TIMESTAMP',
                         default=argparse.SUPPRESS,
                         help="Get results which were detected BEFORE the "
                              "given date and NOT FIXED BEFORE the given "
                              "date. The detection date of a report is "
                              "the storage date when the report was stored to "
                              "the server for the first time. The format of "
                              "TIMESTAMP is "
                              "'year:month:day:hour:minute:second' (the "
                              "\"time\" part can be omitted, in which case "
                              "midnight (00:00:00) is used).")

    f_group.add_argument('--file',
                         nargs='*',
                         dest="file_path",
                         metavar='FILE_PATH',
                         default=init_default('file_path'),
                         help="Filter results by file path. "
                              "The file path can contain multiple * "
                              "quantifiers which matches any number of "
                              "characters (zero or more). So if you have "
                              "/a/x.cpp and /a/y.cpp then \"/a/*.cpp\" "
                              "selects both.")

    f_group.add_argument('--checker-name',
                         nargs='*',
                         dest="checker_name",
                         metavar='CHECKER_NAME',
                         default=init_default('checker_name'),
                         help="Filter results by checker names. "
                              "The checker name can contain multiple * "
                              "quantifiers which matches any number of "
                              "characters (zero or more). So for example "
                              "\"*DeadStores\" will matches "
                              "\"deadcode.DeadStores\"")

    f_group.add_argument('--checker-msg',
                         nargs='*',
                         dest="checker_msg",
                         metavar='CHECKER_MSG',
                         default=init_default('checker_msg'),
                         help="Filter results by checker messages."
                              "The checker message can contain multiple * "
                              "quantifiers which matches any number of "
                              "characters (zero or more).")

    f_group.add_argument('--analyzer-name',
                         nargs='*',
                         dest="analyzer_name",
                         metavar='ANALYZER_NAME',
                         default=init_default('analyzer_name'),
                         help="Filter results by analyzer names. "
                              "The analyzer name can contain multiple * "
                              "quantifiers which match any number of "
                              "characters (zero or more). So for example "
                              "\"clang*\" will match \"clangsa\" and "
                              "\"clang-tidy\".")

    f_group.add_argument('--component',
                         nargs='*',
                         dest="component",
                         metavar='COMPONENT',
                         default=argparse.SUPPRESS,
                         help="Filter results by source components." +
                         warn_diff_mode)

    f_group.add_argument('--detected-at',
                         type=valid_time,
                         dest="detected_at",
                         metavar='TIMESTAMP',
                         default=argparse.SUPPRESS,
                         help="DEPRECATED. Use the '--detected-after/"
                              "--detected-before' options to filter results "
                              "by detection date. Filter results by fix date "
                              "(fixed after the given date) if the "
                              "--detection-status filter option is set only "
                              "to Resolved otherwise it filters the results "
                              "by detection date (detected after the given "
                              "date). The format of TIMESTAMP is "
                              "'year:month:day:hour:minute:second' (the "
                              "\"time\" part can be omitted, in which case "
                              "midnight (00:00:00) is used).")

    f_group.add_argument('--fixed-at',
                         type=valid_time,
                         dest="fixed_at",
                         metavar='TIMESTAMP',
                         default=argparse.SUPPRESS,
                         help="DEPRECATED. Use the '--fixed-after/"
                              "--fixed-before' options to filter results "
                              "by fix date. Filter results by fix date (fixed "
                              "before the given date) if the "
                              "--detection-status filter option is set only "
                              "to Resolved otherwise it filters the results "
                              "by detection date (detected before the given "
                              "date). The format of TIMESTAMP is "
                              "'year:month:day:hour:minute:second' (the "
                              "\"time\" part can be omitted, in which case "
                              "midnight (00:00:00) is used).")

    f_group.add_argument('--detected-before',
                         type=valid_time,
                         dest="detected_before",
                         metavar='TIMESTAMP',
                         default=argparse.SUPPRESS,
                         help="Get results which were detected before the "
                              "given date. The detection date of a report is "
                              "the storage date when the report was stored to "
                              "the server for the first time. The format of "
                              "TIMESTAMP is "
                              "'year:month:day:hour:minute:second' (the "
                              "\"time\" part can be omitted, in which case "
                              "midnight (00:00:00) is used).")

    f_group.add_argument('--detected-after',
                         type=valid_time,
                         dest="detected_after",
                         metavar='TIMESTAMP',
                         default=argparse.SUPPRESS,
                         help="Get results which were detected after the "
                              "given date. The detection date of a report is "
                              "the storage date when the report was stored to "
                              "the server for the first time. The format of "
                              "TIMESTAMP is "
                              "'year:month:day:hour:minute:second' (the "
                              "\"time\" part can be omitted, in which case "
                              "midnight (00:00:00) is used).")

    f_group.add_argument('--fixed-before',
                         type=valid_time,
                         dest="fixed_before",
                         metavar='TIMESTAMP',
                         default=argparse.SUPPRESS,
                         help="Get results which were fixed before the "
                              "given date. The format of TIMESTAMP is "
                              "'year:month:day:hour:minute:second' (the "
                              "\"time\" part can be omitted, in which case "
                              "midnight (00:00:00) is used).")

    f_group.add_argument('--fixed-after',
                         type=valid_time,
                         dest="fixed_after",
                         metavar='TIMESTAMP',
                         default=argparse.SUPPRESS,
                         help="Get results which were fixed after the "
                              "given date. The format of TIMESTAMP is "
                              "'year:month:day:hour:minute:second' (the "
                              "\"time\" part can be omitted, in which case "
                              "midnight (00:00:00) is used).")

    f_group.add_argument('-s', '--suppressed',
                         default=argparse.SUPPRESS,
                         dest="suppressed",
                         action='store_true',
                         help="DEPRECATED. Use the '--filter' option to get "
                              "false positive (suppressed) results. Show only "
                              "suppressed results instead of only "
                              "unsuppressed ones.")

    f_group.add_argument('--filter',
                         type=str,
                         dest='filter',
                         default=argparse.SUPPRESS,
                         help="DEPRECATED. Filter results. Use separated "
                              "filter options to filter the results. The "
                              "filter string has the following format: "
                              "[<SEVERITIES>]:[<CHECKER_NAMES>]:"
                              "[<FILE_PATHS>]:[<DETECTION_STATUSES>]:"
                              "[<REVIEW_STATUSES>] where severites, "
                              "checker_names, file_paths, detection_statuses, "
                              "review_statuses should be a comma separated "
                              "list, e.g.: \"high,medium:unix,core:*.cpp,*.h:"
                              "new,unresolved:false_positive,intentional\"")


def __register_results(parser):
    """
    Add argparse subcommand parser for the "list analysis results" action.
    """

    parser.add_argument(type=str,
                        nargs='+',
                        dest="names",
                        metavar='RUN_NAMES',
                        help="Names of the analysis runs to show result "
                             "summaries of. This has the following format: "
                             "<run_name_1> <run_name_2> <run_name_3> "
                             "where run names can contain * quantifiers which "
                             "matches any number of characters (zero or "
                             "more). So if you have run_1_a_name, "
                             "run_2_b_name, run_2_c_name, run_3_d_name then "
                             "\"run_2* run_3_d_name\" selects the last three "
                             "runs. Use 'CodeChecker cmd runs' to get the "
                             "available runs.")

    parser.add_argument('--details',
                        dest="details",
                        action="store_true",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Get report details for reports such as bug path "
                             "events, bug report points etc.")

    __add_filtering_arguments(parser, DEFAULT_FILTER_VALUES)


def __register_diff(parser):
    """
    Add argparse subcommand parser for the "diff results" action.
    """

    parser.add_argument('-b', '--basename',
                        type=str,
                        nargs='+',
                        dest="base_run_names",
                        metavar='BASE_RUNS',
                        default=argparse.SUPPRESS,
                        help="The 'base' (left) side of the difference: these "
                             "analysis runs are used as the initial state in "
                             "the comparison. The parameter can be multiple "
                             "run names (on the remote server), multiple "
                             "local report directories (result of the analyze "
                             "command) or baseline files (generated by the "
                             "'CodeChecker parse -e baseline' command). In "
                             "case of run name the the basename can contain * "
                             "quantifiers which matches any number of "
                             "characters (zero or more). So if you have "
                             "run-a-1, run-a-2 and run-b-1 then \"run-a*\" "
                             "selects the first two. In case of run names tag "
                             "labels can also be used separated by a colon "
                             "(:) character: \"run_name:tag_name\". A run "
                             "name containing a literal colon (:) must be "
                             "escaped: \"run\\:name\".")

    parser.add_argument('-n', '--newname',
                        type=str,
                        nargs='+',
                        dest="new_run_names",
                        metavar='NEW_RUNS',
                        default=argparse.SUPPRESS,
                        help="The 'new' (right) side of the difference: these "
                             "analysis runs are compared to the -b/--basename "
                             "runs. The parameter can be multiple run names "
                             "(on the remote server), multiple local "
                             "report directories (result of the analyze "
                             "command) or baseline files (generated by the "
                             "'CodeChecker parse -e baseline' command). In "
                             "case of run name the newname can contain * "
                             "quantifiers which matches any number of "
                             "characters (zero or more). So if you have "
                             "run-a-1, run-a-2 and run-b-1 then "
                             "\"run-a*\" selects the first two. In case of "
                             "run names tag labels can also be used separated "
                             "by a colon (:) character: "
                             "\"run_name:tag_name\". A run "
                             "name containing a literal colon (:) must be "
                             "escaped: \"run\\:name\".")

    parser.add_argument('--print-steps',
                        dest="print_steps",
                        action="store_true",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Print the steps the analyzers took in finding "
                             "the reported defect.")

    __add_filtering_arguments(parser, DEFAULT_FILTER_VALUES, True)

    group = parser.add_argument_group(
        "comparison modes",
        "List reports that can be found only in baseline or new runs or in "
        "both. False positive and intentional reports are considered as "
        "resolved, i.e. these are excluded from the report set as if they "
        "were not reported.")
    group = group.add_mutually_exclusive_group(required=True)

    group.add_argument('--new',
                       dest="new",
                       default=argparse.SUPPRESS,
                       action='store_true',
                       help="Show results that didn't exist in the 'base' "
                            "but appear in the 'new' run.")

    group.add_argument('--resolved',
                       dest="resolved",
                       default=argparse.SUPPRESS,
                       action='store_true',
                       help="Show results that existed in the 'base' but "
                            "disappeared from the 'new' run.")

    group.add_argument('--unresolved',
                       dest="unresolved",
                       default=argparse.SUPPRESS,
                       action='store_true',
                       help="Show results that appear in both the 'base' and "
                            "the 'new' run.")

    def __handle(args):
        """Custom handler for 'diff' so custom error messages can be
        printed without having to capture 'parser' in main."""

        output_dir = ['-e', '--export-dir']
        if args.output_format == 'html' and \
           not any(util.arg_match(output_dir, sys.argv[1:])):
            parser.error("argument --output html: not allowed without "
                         "argument --export-dir")

        cmd_line_client.handle_diff_results(args)

    parser.set_defaults(func=__handle)


def __register_sum(parser):
    """
    Add argparse subcommand parser for the "list result count by checker"
    action.
    """

    name_group = parser.add_mutually_exclusive_group(required=True)

    name_group.add_argument('-n', '--name',
                            type=str,
                            nargs='+',
                            dest="names",
                            metavar='RUN_NAME',
                            default=argparse.SUPPRESS,
                            help="Names of the analysis runs to show result "
                                 "count breakdown for. This has the following "
                                 "format: <run_name_1>:<run_name_2>:"
                                 "<run_name_3> where run names can contain "
                                 "multiple * quantifiers which matches any "
                                 "number of characters (zero or more). So if "
                                 "you have run_1_a_name, run_2_b_name, "
                                 "run_2_c_name, run_3_d_name then "
                                 "\"run_2*:run_3_d_name\" selects the last "
                                 "three runs. Use 'CodeChecker cmd runs' to "
                                 "get the available runs.")

    name_group.add_argument('-a', '--all',
                            dest="all_results",
                            action='store_true',
                            default=argparse.SUPPRESS,
                            help="Show breakdown for all analysis runs.")

    parser.add_argument('--disable-unique',
                        dest="disable_unique",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="DEPRECATED. Use the '--uniqueing' option to "
                             "get uniqueing results. List all bugs even if "
                             "these end up in the same bug location, but "
                             "reached through different paths. By uniqueing "
                             "the bugs a report will be appeared only once "
                             "even if it is found on several paths.")

    default_filter_values = DEFAULT_FILTER_VALUES
    default_filter_values['uniqueing'] = 'on'
    __add_filtering_arguments(parser, default_filter_values)


def __register_delete(parser):
    """
    Add argparse subcommand parser for the "delete runs" action.
    """

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-n', '--name',
                       type=str,
                       nargs='+',
                       dest="names",
                       metavar='RUN_NAME',
                       default=argparse.SUPPRESS,
                       help="Full name(s) of the analysis run or runs to "
                            "delete.")

    group.add_argument('--all-before-run',
                       type=str,
                       dest="all_before_run",
                       metavar='RUN_NAME',
                       default=argparse.SUPPRESS,
                       help="Delete all runs that were stored to the server "
                            "BEFORE the specified one.")

    group.add_argument('--all-after-run',
                       type=str,
                       dest="all_after_run",
                       metavar='RUN_NAME',
                       default=argparse.SUPPRESS,
                       help="Delete all runs that were stored to the server "
                            "AFTER the specified one.")

    group.add_argument('--all-after-time',
                       type=valid_time,
                       dest="all_after_time",
                       metavar='TIMESTAMP',
                       default=argparse.SUPPRESS,
                       help="Delete all analysis runs that were stored to the "
                            "server AFTER the given timestamp. The format of "
                            "TIMESTAMP is "
                            "'year:month:day:hour:minute:second' (the "
                            "\"time\" part can be omitted, in which case "
                            "midnight (00:00:00) is used).")

    group.add_argument('--all-before-time',
                       type=valid_time,
                       dest="all_before_time",
                       metavar='TIMESTAMP',
                       default=argparse.SUPPRESS,
                       help="Delete all analysis runs that were stored to the "
                            "server BEFORE the given timestamp. The format of "
                            "TIMESTAMP is "
                            "'year:month:day:hour:minute:second' (the "
                            "\"time\" part can be omitted, in which case "
                            "midnight (00:00:00) is used).")


def __register_update(parser):
    """
    Add argparse subcommand parser for the "update" run action.
    """

    parser.add_argument('run_name',
                        type=str,
                        default=argparse.SUPPRESS,
                        help="Full name of the analysis run to update.")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-n', '--name',
                       type=str,
                       dest="new_run_name",
                       metavar='NEW_RUN_NAME',
                       default=argparse.SUPPRESS,
                       help="Name name of the analysis run.")


def __register_suppress(parser):
    """
    Add argparse subcommand parser for the "suppress file management" action.
    """

    parser.add_argument(type=str,
                        dest="name",
                        metavar='RUN_NAME',
                        default=argparse.SUPPRESS,
                        help="Name of the analysis run to suppress or "
                             "unsuppress a report in.")

    parser.add_argument('-f', '--force',
                        dest="force",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Enable suppression of already suppressed "
                             "reports.")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-i', '--import',
                       type=str,
                       dest="input",
                       metavar='SUPPRESS_FILE',
                       default=argparse.SUPPRESS,
                       help="Import suppression from the suppress file into "
                            "the database.")


def __register_products(parser):
    """
    Add argparse subcommand parser for the "product management" action.
    """

    def __register_add(parser):
        """
        Add argparse subcommand parser for the "add new product" action.
        """
        parser.add_argument("endpoint",
                            type=str,
                            metavar='ENDPOINT',
                            default=argparse.SUPPRESS,
                            help="The URL endpoint where clients can access "
                                 "the analysis results for this product.")

        parser.add_argument('-n', '--name',
                            type=str,
                            dest="display_name",
                            default=argparse.SUPPRESS,
                            required=False,
                            help="A custom display name for the product, "
                                 "which will be shown in the viewer. This "
                                 "is purely for decoration and user "
                                 "experience, program calls use the "
                                 "<ENDPOINT>.")

        parser.add_argument('--description',
                            type=str,
                            dest="description",
                            default=argparse.SUPPRESS,
                            required=False,
                            help="A custom textual description to be shown "
                                 "alongside the product.")

        dbmodes = parser.add_argument_group(
            "database arguments",
            "NOTE: These database arguments are relative to the server "
            "machine, as it is the server which will make the database "
            "connection.")

        dbmodes = dbmodes.add_mutually_exclusive_group(required=False)

        SQLITE_PRODUCT_ENDPOINT_DEFAULT_VAR = '<ENDPOINT>.sqlite'
        dbmodes.add_argument('--sqlite',
                             type=str,
                             dest="sqlite",
                             metavar='SQLITE_FILE',
                             default=SQLITE_PRODUCT_ENDPOINT_DEFAULT_VAR,
                             required=False,
                             help="Path of the SQLite database file to use. "
                                  "Not absolute paths will be relative to "
                                  "the server's <CONFIG_DIRECTORY>.")

        dbmodes.add_argument('--postgresql',
                             dest="postgresql",
                             action='store_true',
                             required=False,
                             default=argparse.SUPPRESS,
                             help="Specifies that a PostgreSQL database is "
                                  "to be used instead of SQLite. See the "
                                  "\"PostgreSQL arguments\" section on how "
                                  "to configure the database connection.")

        PGSQL_PRODUCT_ENDPOINT_DEFAULT_VAR = '<ENDPOINT>'
        pgsql = parser.add_argument_group(
            "PostgreSQL arguments",
            "Values of these arguments are ignored, unless '--postgresql' is "
            "specified! The database specified here must exist, and be "
            "connectible by the server.")

        # TODO: --dbSOMETHING arguments are kept to not break interface from
        # old command. Database using commands such as "CodeChecker store" no
        # longer supports these --- it would be ideal to break and remove args
        # with this style and only keep --db-SOMETHING.
        pgsql.add_argument('--dbaddress', '--db-host',
                           type=str,
                           dest="dbaddress",
                           default="localhost",
                           required=False,
                           help="Database server address.")

        pgsql.add_argument('--dbport', '--db-port',
                           type=int,
                           dest="dbport",
                           default=5432,
                           required=False,
                           help="Database server port.")

        pgsql.add_argument('--dbusername', '--db-username',
                           type=str,
                           dest="dbusername",
                           default=PGSQL_PRODUCT_ENDPOINT_DEFAULT_VAR,
                           required=False,
                           help="Username to use for connection.")

        pgsql.add_argument('--dbpassword', '--db-password',
                           type=str,
                           dest="dbpassword",
                           default="",
                           required=False,
                           help="Password to use for authenticating the "
                                "connection.")

        pgsql.add_argument('--dbname', '--db-name',
                           type=str,
                           dest="dbname",
                           default=PGSQL_PRODUCT_ENDPOINT_DEFAULT_VAR,
                           required=False,
                           help="Name of the database to use.")

        def __handle(args):
            """Custom handler for 'add' so custom error messages can be
            printed without having to capture 'parser' in main."""

            def arg_match(options):
                """Checks and selects the option string specified in 'options'
                that are present in the invocation argv."""
                matched_args = []
                for option in options:
                    if any([arg if option.startswith(arg) else None
                            for arg in sys.argv[1:]]):
                        matched_args.append(option)
                        continue

                return matched_args

            # See if there is a "PostgreSQL argument" specified in the
            # invocation without '--postgresql' being there. There is no way
            # to distinguish a default argument and a deliberately specified
            # argument without inspecting sys.argv.
            options = ['--dbaddress', '--dbport', '--dbusername', '--dbname',
                       '--db-host', '--db-port', '--db-username', '--db-name']
            psql_args_matching = arg_match(options)
            if any(psql_args_matching) and \
                    'postgresql' not in args:
                first_matching_arg = next(iter([match for match
                                                in psql_args_matching]))
                parser.error("argument {0}: not allowed without argument "
                             "--postgresql".format(first_matching_arg))
                # parser.error() terminates with return code 2.

            # Some arguments get a dynamic default value that depends on the
            # value of another argument.
            if args.sqlite == SQLITE_PRODUCT_ENDPOINT_DEFAULT_VAR:
                args.sqlite = args.endpoint + '.sqlite'

            if args.dbusername == PGSQL_PRODUCT_ENDPOINT_DEFAULT_VAR:
                args.dbusername = args.endpoint

            if args.dbname == PGSQL_PRODUCT_ENDPOINT_DEFAULT_VAR:
                args.dbname = args.endpoint

            if 'postgresql' not in args:
                # The --db-SOMETHING arguments are irrelevant if --postgresql
                # is not used.
                delattr(args, 'dbaddress')
                delattr(args, 'dbport')
                delattr(args, 'dbusername')
                delattr(args, 'dbpassword')
                delattr(args, 'dbname')
            else:
                # If --postgresql is given, --sqlite is useless.
                delattr(args, 'sqlite')

            # If everything is fine, do call the handler for the subcommand.
            product_client.handle_add_product(args)

        parser.set_defaults(func=__handle)

    def __register_del(parser):
        """
        Add argparse subcommand parser for the "delete product" action.
        """
        parser.add_argument("endpoint",
                            type=str,
                            metavar='ENDPOINT',
                            default=argparse.SUPPRESS,
                            help="The URL endpoint where clients can access "
                                 "the analysis results for the product.")

    subcommands = parser.add_subparsers(title='available actions')

    # Create handlers for individual subcommands.
    list_p = subcommands.add_parser(
        'list',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="List the name and basic information about products "
                    "added to the server.",
        help="List products available on the server.")
    list_p.set_defaults(func=product_client.handle_list_products)
    __add_common_arguments(list_p,
                           needs_product_url=False,
                           output_formats=DEFAULT_OUTPUT_FORMATS)

    add = subcommands.add_parser(
        'add',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Create a new product to be managed by the server by "
                    "providing the product's details and database connection.",
        help="Register a new product to the server.")
    __register_add(add)
    __add_common_arguments(add, needs_product_url=False)

    del_p = subcommands.add_parser(
        'del',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Removes the specified product from the list of products "
                    "managed by the server. NOTE: This only removes the "
                    "association and disconnects the server from the "
                    "database -- NO actual ANALYSIS DATA is REMOVED. "
                    "Configuration, such as access control, however, WILL BE "
                    "LOST!",
        help="Delete a product from the server's products.")
    __register_del(del_p)
    del_p.set_defaults(func=product_client.handle_del_product)
    __add_common_arguments(del_p, needs_product_url=False)


def __register_source_components(parser):
    """
    Add argparse subcommand parser for the "source component management"
    action.
    """

    def __register_add(parser):
        parser.add_argument("name",
                            type=str,
                            metavar='NAME',
                            default=argparse.SUPPRESS,
                            help="Unique name of the source component.")

        parser.add_argument('--description',
                            type=str,
                            dest="description",
                            default=argparse.SUPPRESS,
                            required=False,
                            help="A custom textual description to be shown "
                                 "alongside the source component.")

        parser.add_argument('-i', '--import',
                            type=str,
                            dest="component_file",
                            metavar='COMPONENT_FILE',
                            default=argparse.SUPPRESS,
                            required=True,
                            help="R|Path to the source component file which "
                                 "contains multiple file paths. Each file "
                                 "path should start with a '+' or '-' sign. "
                                 "Results will be listed only from paths with "
                                 "a '+' sign. "
                                 "Results will not be listed from paths with "
                                 "a '-' sign. Let's assume there are three "
                                 "directories: test_files, test_data and "
                                 "test_config. In the given example only the "
                                 "results from the test_files and test_data "
                                 "directories will be listed.\n"
                                 "E.g.: \n"
                                 "  +*/test*/*\n"
                                 "  -*/test_dat*/*\n"
                                 "Please see the User guide for more "
                                 "information.")

    def __register_del(parser):
        """
        Add argparse subcommand parser for the "del component" action.
        """
        parser.add_argument("name",
                            type=str,
                            metavar='NAME',
                            default=argparse.SUPPRESS,
                            help="Name of the source component name which "
                                 "will be removed.")

    subcommands = parser.add_subparsers(title='available actions')

    # Create handlers for individual subcommands.
    list_components = subcommands.add_parser(
        'list',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="List the name and basic information about source "
                    "component added to the server.",
        help="List source components available on the server.")
    list_components.set_defaults(
        func=source_component_client.handle_list_components)
    __add_common_arguments(list_components,
                           output_formats=DEFAULT_OUTPUT_FORMATS)

    add = subcommands.add_parser(
        'add',
        formatter_class=arg.RawDescriptionDefaultHelpFormatter,
        description="Creates a new source component or updates an existing "
                    "one.",
        help="Creates/updates a source component.")
    __register_add(add)
    add.set_defaults(func=source_component_client.handle_add_component)
    __add_common_arguments(add)

    del_c = subcommands.add_parser(
        'del',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Removes the specified source component.",
        help="Delete a source component from the server.")
    __register_del(del_c)
    del_c.set_defaults(func=source_component_client.handle_del_component)
    __add_common_arguments(del_c)


def __register_login(parser):
    """
    Add argparse subcommand parser for the "handle authentication" action.
    """

    parser.add_argument(type=str,
                        dest="username",
                        metavar='USERNAME',
                        nargs='?',
                        default=getpass.getuser(),
                        help="The username to authenticate with.")

    parser.add_argument('-d', '--deactivate', '--logout',
                        dest="logout",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Send a logout request to end your privileged "
                             "session.")


def __register_runs(parser):
    """
    Add argparse subcommand parser for the "list runs by run name" action.
    """

    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument('-n', '--name',
                       type=str,
                       nargs='*',
                       dest="names",
                       metavar='RUN_NAME',
                       default=argparse.SUPPRESS,
                       required=False,
                       help="Names of the analysis runs. If this argument is "
                            "not supplied it will show all runs. This has "
                            "the  following format: \"<run_name_1> "
                            "<run_name_2> <run_name_3>\" where run names can "
                            "contain multiple * quantifiers which matches "
                            "any number of characters (zero or more). So if "
                            "you have run_1_a_name, run_2_b_name, "
                            "run_2_c_name, run_3_d_name then \"run_2* "
                            "run_3_d_name\" shows the last three runs.")

    group.add_argument('--details',
                       default=argparse.SUPPRESS,
                       action='store_true',
                       required=False,
                       help="Adds extra details to the run information in "
                            "JSON format, such as the list of files that are "
                            "failed to analyze.")

    group.add_argument('--all-before-run',
                       type=str,
                       dest="all_before_run",
                       metavar='RUN_NAME',
                       default=argparse.SUPPRESS,
                       help="Get all runs that were stored to the server "
                            "BEFORE the specified one.")

    group.add_argument('--all-after-run',
                       type=str,
                       dest="all_after_run",
                       metavar='RUN_NAME',
                       default=argparse.SUPPRESS,
                       help="Get all runs that were stored to the server "
                            "AFTER the specified one.")

    group.add_argument('--all-after-time',
                       type=valid_time,
                       dest="all_after_time",
                       metavar='TIMESTAMP',
                       default=argparse.SUPPRESS,
                       help="Get all analysis runs that were stored to "
                            "the server AFTER the given timestamp. The "
                            "format of TIMESTAMP is "
                            "'year:month:day:hour:minute:second' (the "
                            "\"time\" part can be omitted, in which case "
                            "midnight (00:00:00) is used).")

    group.add_argument('--all-before-time',
                       type=valid_time,
                       dest="all_before_time",
                       metavar='TIMESTAMP',
                       default=argparse.SUPPRESS,
                       help="Get all analysis runs that were stored to "
                            "the server BEFORE the given timestamp. The "
                            "format of TIMESTAMP is "
                            "'year:month:day:hour:minute:second' (the "
                            "\"time\" part can be omitted, in which case "
                            "midnight (00:00:00) is used).")

    # Get available sort types.
    sort_type_values = list(ttypes.RunSortType._NAMES_TO_VALUES.values())
    sort_types = [cmd_line_client.run_sort_type_str(s)
                  for s in sort_type_values]

    # Set 'date' as a default sort type.
    default_sort_type = sort_types[
        sort_type_values.index(ttypes.RunSortType.DATE)]

    parser.add_argument('--sort',
                        dest="sort_type",
                        required=False,
                        choices=sort_types,
                        default=default_sort_type,
                        help="Sort run data by this column.")

    # Get available order types.
    order_type_names = list(ttypes.Order._NAMES_TO_VALUES.keys())
    order_types = [s.lower() for s in order_type_names]

    # Set 'desc' as a default order type.
    order_type_values = list(ttypes.Order._NAMES_TO_VALUES.values())
    default_order_type = order_types[
        order_type_values.index(ttypes.Order.DESC)]

    parser.add_argument('--order',
                        dest="sort_order",
                        required=False,
                        choices=order_types,
                        default=default_order_type,
                        help="Sort order of the run data.")


def __register_run_histories(parser):
    """
    Add argparse subcommand parser for the "list run histories by run name"
    action.
    """

    parser.add_argument('-n', '--name',
                        type=str,
                        nargs='*',
                        dest="names",
                        metavar='RUN_NAME',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Names of the analysis runs to show history for. "
                             "If this argument is not supplied it will show "
                             "the history for all runs. This has the "
                             "following format: \"<run_name_1> <run_name_2> "
                             "<run_name_3>\" where run names can contain "
                             "multiple * quantifiers which matches any number "
                             "of characters (zero or more). So if you have "
                             "run_1_a_name, run_2_b_name, run_2_c_name, "
                             "run_3_d_name then \"run_2* run_3_d_name\" shows "
                             "history for the last three runs. Use "
                             "'CodeChecker cmd runs' to get the available "
                             "runs.")


def __register_export(parser):
    """
    Add argparser subcommand for the "export run by run name action"
    """
    parser.add_argument('-n', '--name',
                        type=str,
                        nargs='+',
                        dest="names",
                        metavar='RUN_NAME',
                        default=argparse.SUPPRESS,
                        help="Name of the analysis run.")


def __register_importer(parser):
    """
    Add argparser subcommand for the "import run by run name action"
    """

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--import',
                       type=str,
                       dest="input",
                       metavar='JSON_FILE',
                       default=argparse.SUPPRESS,
                       help="Import findings from the json file into "
                       "the database.")


def __register_permissions(parser):
    """
    Add argparse subcommand parser for the "handle permissions" action.
    """
    parser.add_argument('-o', '--output',
                        dest="output_format",
                        required=False,
                        default="json",
                        choices=['json'],
                        help="The output format to use in showing the data.")


def __register_token(parser):
    """
    Add argparse subcommand parser for the "handle token" action.
    """

    def __register_new(parser):
        parser.add_argument("--description",
                            type=str,
                            metavar='DESCRIPTION',
                            default=argparse.SUPPRESS,
                            required=False,
                            help="A custom textual description to be shown "
                                 "alongside the token.")

    def __register_del(parser):
        """
        Add argparse subcommand parser for the "del token" action.
        """
        parser.add_argument("token",
                            type=str,
                            metavar='TOKEN',
                            default=argparse.SUPPRESS,
                            help="Personal access token which will be "
                                 "deleted.")

    subcommands = parser.add_subparsers(title='available actions')

    # Create handlers for individual subcommands.
    list_tokens = subcommands.add_parser(
        'list',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="List the available personal access tokens.",
        help="List tokens available on the server.")
    list_tokens.set_defaults(
        func=token_client.handle_list_tokens)
    __add_common_arguments(list_tokens,
                           needs_product_url=False,
                           output_formats=DEFAULT_OUTPUT_FORMATS)

    new_t = subcommands.add_parser(
        'new',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Creating a new personal access token.",
        help="Creates a new personal access token.")
    __register_new(new_t)
    new_t.set_defaults(func=token_client.handle_add_token)
    __add_common_arguments(new_t, needs_product_url=False)

    del_t = subcommands.add_parser(
        'del',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Removes the specified access token.",
        help="Deletes a token from the server.")
    __register_del(del_t)
    del_t.set_defaults(func=token_client.handle_del_token)
    __add_common_arguments(del_t, needs_product_url=False)


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    subcommands = parser.add_subparsers(title='available actions')

    # Create handlers for individual subcommands.
    runs = subcommands.add_parser(
        'runs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="List the analysis runs available on the server.",
        help="List the available analysis runs.")
    __register_runs(runs)
    runs.set_defaults(func=cmd_line_client.handle_list_runs)
    __add_common_arguments(runs, output_formats=DEFAULT_OUTPUT_FORMATS)

    run_histories = subcommands.add_parser(
        'history',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Show run history for some analysis runs.",
        help="Show run history of multiple runs.")
    __register_run_histories(run_histories)
    run_histories.set_defaults(func=cmd_line_client.handle_list_run_histories)
    __add_common_arguments(run_histories,
                           output_formats=DEFAULT_OUTPUT_FORMATS)

    results = subcommands.add_parser(
        'results',
        formatter_class=arg.RawDescriptionDefaultHelpFormatter,
        description="Show the individual analysis reports' summary.",
        help="List analysis result (finding) summary for a given run.",
        epilog='''Example scenario: List analysis results
------------------------------------------------
Get analysis results for a run:
    CodeChecker cmd results my_run

Get analysis results for multiple runs:
    CodeChecker cmd results my_run1 my_run2

Get analysis results by using regex:
    CodeChecker cmd results "my_run*"

Get analysis results for a run and filter the analysis results:
    CodeChecker cmd results my_run --severity critical high medium \\
        --file "/home/username/my_project/*"

    CodeChecker cmd results my_run --review-status confirmed unreviewed \\
        --component my_component_name''')
    __register_results(results)
    results.set_defaults(func=cmd_line_client.handle_list_results)
    __add_common_arguments(results, output_formats=DEFAULT_OUTPUT_FORMATS)

    diff = subcommands.add_parser(
        'diff',
        formatter_class=arg.RawDescriptionDefaultHelpFormatter,
        description="Compare two analysis runs to show the results that "
                    "differ between the two.",
        help="Compare two analysis runs and show the difference.",
        epilog='''
envionment variables:
  CC_REPO_DIR         Root directory of the sources, i.e. the directory where
                      the repository was cloned. Use it when generating gerrit
                      output.
  CC_REPORT_URL       URL where the report can be found. Use it when generating
                      gerrit output.
  CC_CHANGED_FILES    Path of changed files json from Gerrit. Use it when
                      generating gerrit output.

Exit status
------------------------------------------------
0 - No difference between baseline and newrun
1 - CodeChecker error
2 - There is at least one report difference between baseline and newrun

Example scenario: Compare multiple analysis runs
------------------------------------------------
Compare two runs and show results that didn't exist in the 'run1' but appear in
the 'run2' run:
    CodeChecker cmd diff -b run1 -n run2 --new

Compare a remote run with a local report directory and show results that didn't
exist in the remote run 'run1' but appear in the local report directory:
    CodeChecker cmd diff -b run1 -n /my_report_dir --new

Compare two runs and show results that exist in both runs and filter results
by multiple severity values:
    CodeChecker cmd diff -b run1 -n run2 --unresolved --severity high medium

Compare a baseline file (generated by the 'CodeChecker parse -e baseline'
command) and a local report directory and show new results:
    CodeChecker cmd diff -b /reports.baseline -n /my_report_dir --new'''
    )
    __register_diff(diff)

    diff_output_formats = DEFAULT_OUTPUT_FORMATS + ["html", "gerrit",
                                                    "codeclimate"]
    output_help_msg = "R|The output format(s) to use in showing the data.\n" \
                      "- html: multiple html files will be generated in the " \
                      "export directory.\n" \
                      "- gerrit: a 'gerrit_review.json' file will be " \
                      "generated in the export directory.\n" \
                      "- codeclimate: a 'codeclimate_issues.json' file will " \
                      "be generated in the export directory.\n" \
                      "For the output formats (json, gerrit, codeclimate) " \
                      "if an export directory is set the output files will " \
                      "be generated if not the results are printed to the " \
                      "stdout but only if one format was selected."

    __add_common_arguments(diff,
                           output_formats=diff_output_formats,
                           output_help_message=output_help_msg,
                           allow_multiple_outputs=True)

    sum_p = subcommands.add_parser(
        'sum',
        formatter_class=arg.RawDescriptionDefaultHelpFormatter,
        description="Show checker statistics for some analysis runs.",
        help="Show statistics of checkers.",
        epilog='''Example scenario: Get checker statistics
------------------------------------------------
Get statistics for a run:
    CodeChecker cmd sum -n my_run

Get statistics for all runs filtered by multiple checker names:
    CodeChecker cmd sum --all --checker-name "core.*" "deadcode.*"

Get statistics for all runs and only for severity 'high':
    CodeChecker cmd sum --all --severity "high"''')
    __register_sum(sum_p)
    sum_p.set_defaults(func=cmd_line_client.handle_list_result_types)
    __add_common_arguments(sum_p, output_formats=DEFAULT_OUTPUT_FORMATS)

    token = subcommands.add_parser(
        'token',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Access subcommands related to configuring personal "
                    "access tokens managed by a CodeChecker server. Please "
                    "see the individual subcommands for details.",
        help="Access subcommands related to configuring personal access "
             "tokens managed by a CodeChecker server.")
    __register_token(token)

    del_p = subcommands.add_parser(
        'del',
        formatter_class=arg.RawDescriptionDefaultHelpFormatter,
        description="""
Remove analysis runs from the server based on some criteria.

!!! WARNING !!! When a run is deleted, ALL associated information (reports,
files, run histories) is PERMANENTLY LOST! Please be careful with this command
because it can not be undone.

NOTE! You can't remove a snapshot of run (a run history), you can remove only
full runs.""",
        help="Delete analysis runs.")
    __register_delete(del_p)
    del_p.set_defaults(func=cmd_line_client.handle_remove_run_results)
    __add_common_arguments(del_p)

    update_p = subcommands.add_parser(
        'update',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Update the name of an analysis run.",
        help="Update an analysis run.")
    __register_update(update_p)
    update_p.set_defaults(func=cmd_line_client.handle_update_run)
    __add_common_arguments(update_p)

    suppress = subcommands.add_parser(
        'suppress',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Imports suppressions from a suppress file to a "
                    "CodeChecker server.",
        help="Manage and import suppressions of a CodeChecker server.")
    __register_suppress(suppress)
    suppress.set_defaults(func=cmd_line_client.handle_suppress)
    __add_common_arguments(suppress)

    products = subcommands.add_parser(
        'products',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="CodeChecker organises its databases into products. "
                    "Each product has an individually configured database "
                    "which stores the analysis results. These subcommands "
                    "are used to manage the products configured by the "
                    "server. Please see the individual subcommands for "
                    "details.",
        epilog="Most of these commands require authentication and "
               "appropriate access rights. Please see 'CodeChecker cmd "
               "login' to authenticate.",
        help="Access subcommands related to configuring the products managed "
             "by a CodeChecker server.")
    __register_products(products)
    __add_common_arguments(products, needs_product_url=None)

    components = subcommands.add_parser(
        'components',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Source components are named collection of directories "
                    "specified as directory filter.",
        help="Access subcommands related to configuring the source components "
             "managed by a CodeChecker server.")
    __register_source_components(components)
    __add_common_arguments(components)

    login = subcommands.add_parser(
        'login',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Certain CodeChecker servers can require elevated "
                    "privileges to access analysis results. In such cases "
                    "it is mandatory to authenticate to the server. This "
                    "action is used to perform an authentication in the "
                    "command-line.",
        help="Authenticate into CodeChecker servers that require privileges.")
    __register_login(login)
    login.set_defaults(func=cmd_line_client.handle_login)
    __add_common_arguments(login, needs_product_url=False)

    export = subcommands.add_parser(
        'export',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Export data (comments, review statuses) from a running "
                    "CodeChecker server into a json format",
        help="Export data from a CodeChecker server to json format."
    )
    __register_export(export)
    export.set_defaults(func=cmd_line_client.handle_export)
    __add_common_arguments(export)

    importer = subcommands.add_parser(
        'import',
        formatter_class=arg.RawDescriptionDefaultHelpFormatter,
        description="Import the results into CodeChecker server",
        help="Import the analysis from a json file exported by the "
             "'CodeChecker cmd export' command into CodeChecker"
    )
    __register_importer(importer)
    importer.set_defaults(func=cmd_line_client.handle_import)
    __add_common_arguments(importer)

    permissions = subcommands.add_parser(
        'permissions',
        formatter_class=arg.RawDescriptionDefaultHelpFormatter,
        description="Get access control information from a CodeChecker "
                    "server. PERMISSION_VIEW access right is required to run "
                    "this command.",
        help="Get access control information from a CodeChecker server."
    )
    __register_permissions(permissions)
    permissions.set_defaults(func=permission_client.handle_permissions)
    __add_common_arguments(permissions, needs_product_url=False)

# 'cmd' does not have a main() method in itself, as individual subcommands are
# handled later on separately.
