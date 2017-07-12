# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
The CodeChechecker command-line client can be used to view information about
analysis reports found on a running viewer 'server' from a command-line.
"""

import argparse
import getpass
import datetime

from libcodechecker import output_formatters
from libcodechecker.cmd import cmd_line_client
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('CMD')


def valid_time(t):
    """
    Constructs a datetime from a 'year:month:day:hour:minute:second'-formatted
    string.
    """

    try:
        parts = map(int, t.split(':'))
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
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

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


def __add_common_arguments(parser, has_matrix_output=False):
    """
    Add some common arguments, like server address and verbosity, to parser.
    """

    common_group = parser.add_argument_group('common arguments')

    common_group.add_argument('--host',
                              type=str,
                              dest="host",
                              default="localhost",
                              required=False,
                              help="The address of the CodeChecker viewer "
                                   "server to connect to.")

    common_group.add_argument('-p', '--port',
                              type=int,
                              dest="port",
                              default=8001,
                              required=False,
                              help="The port the server is running on.")

    if has_matrix_output:
        common_group.add_argument('-o', '--output',
                                  dest="output_format",
                                  required=False,
                                  # TODO: 'plaintext' only kept for legacy.
                                  default="plaintext",
                                  choices=["plaintext"] +
                                          output_formatters.USER_FORMATS,
                                  help="The output format to use in showing "
                                       "the data.")

    add_verbose_arguments(common_group)


def __add_filtering_arguments(parser):
    """
    Add some common filtering arguments to the given parser.
    """

    # TODO: '-s' does not mean suppressed anymore in any other command.
    parser.add_argument('-s', '--suppressed',
                        dest="suppressed",
                        action='store_true',
                        help="Filter results to only show suppressed entries.")

    parser.add_argument('--filter',
                        type=str,
                        dest='filter',
                        default="::",
                        help="Filter results. The filter string has the "
                             "following format: "
                             "<severity>:<checker_name>:<file_path>")


def __register_results(parser):
    """
    Add argparse subcommand parser for the "list analysis results" action.
    """

    # TODO: Turn this into a positional argument!
    # (So the most basic invocation is 'CodeChecker cmd runs my_analysis_run'.)
    parser.add_argument('-n', '--name',
                        type=str,
                        dest="name",
                        metavar='RUN_NAME',
                        required=True,
                        help="Name of the analysis run to show result "
                             "summaries of. Use 'CodeChecker cmd runs' to "
                             "get the available runs.")

    __add_filtering_arguments(parser)


def __register_diff(parser):
    """
    Add argparse subcommand parser for the "diff results" action.
    """

    # TODO: Turn -b and -n into positional arguments: 'diff base new --blabla'.
    parser.add_argument('-b', '--basename',
                        type=str,
                        dest="basename",
                        metavar='BASE_RUN',
                        required=True,
                        default=argparse.SUPPRESS,
                        help="The 'base' (left) side of the difference: this "
                             "analysis run is used as the initial state in "
                             "the comparison.")

    parser.add_argument('-n', '--newname',
                        type=str,
                        dest="newname",
                        metavar='NEW_RUN',
                        required=True,
                        default=argparse.SUPPRESS,
                        help="The 'new' (right) side of the difference: this "
                             "analysis run is compared to the -b/--basename "
                             "run.")

    __add_filtering_arguments(parser)

    group = parser.add_argument_group("comparison modes")
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


def __register_sum(parser):
    """
    Add argparse subcommand parser for the "list result count by checker"
    action.
    """

    name_group = parser.add_mutually_exclusive_group(required=True)

    # TODO: Turn this into a positional argument too.
    name_group.add_argument('-n', '--name',
                            type=str,
                            nargs='+',
                            dest="names",
                            metavar='RUN_NAME',
                            default=argparse.SUPPRESS,
                            help="Names of the analysis runs to show result "
                                 "count breakdown for.")

    name_group.add_argument('-a', '--all',
                            dest="all_results",
                            action='store_true',
                            default=argparse.SUPPRESS,
                            help="Show breakdown for all analysis runs.")

    __add_filtering_arguments(parser)


def __register_delete(parser):
    """
    Add argparse subcommand parser for the "delete runs" action.
    """

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--name',
                       type=str,
                       nargs='+',
                       dest="name",
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


def __register_suppress(parser):
    """
    Add argparse subcommand parser for the "suppress file management" action.
    """

    # TODO: Turn this into a positional argument too.
    parser.add_argument('-n', '--name',
                        type=str,
                        dest="name",
                        metavar='RUN_NAME',
                        required=True,
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

    group.add_argument('-e', '--export',
                       type=str,
                       dest="output",
                       metavar='SUPPRESS_FILE',
                       default=argparse.SUPPRESS,
                       help="Export into a suppress file from suppressions in "
                            "the server's database.")

    group.add_argument('-i', '--import',
                       type=str,
                       dest="input",
                       metavar='SUPPRESS_FILE',
                       default=argparse.SUPPRESS,
                       help="Import suppression from the suppress file into "
                            "the database.")

    # TODO: This could be a positional argument too later on, so invocation
    # for a specific bug is:
    # CodeChecker cmd suppress RUN_NAME BUG_ID -x|-f|--whatever
    group.add_argument('--bugid',
                       type=str,
                       dest="bugid",
                       default=argparse.SUPPRESS,
                       help="Manage suppression of the defect report based "
                            "on its ID.")

    bugid = parser.add_argument_group(
        "per-report arguments",
        "Options here are only applicable is '--bugid' is specified!")

    bugid.add_argument('--file',
                       type=str,
                       dest="file",
                       default=argparse.SUPPRESS,
                       help="Suppress/unsuppress the given report ONLY in the "
                            "specified file, instead of every occurrence of "
                            "it.")

    bugid.add_argument('-x', '--unsuppress',
                       dest="unsuppress",
                       action='store_true',
                       default=argparse.SUPPRESS,
                       help="Unsuppress the specified report. (If not given, "
                            "default action is to suppress a report.)")

    bugid.add_argument('-c', '--comment',
                       type=str,
                       dest="comment",
                       default=argparse.SUPPRESS,
                       help="Specify the (optional) comment which explains "
                            "why the given report is suppressed.")


def __register_auth(parser):
    """
    Add argparse subcommand parser for the "handle authentication" action.
    """

    # TODO: Turn this into a positional argument. An optional one, because -d.
    parser.add_argument('-u', '--username',
                        type=str,
                        dest="username",
                        required=False,
                        default=getpass.getuser(),
                        help="The username to authenticate with.")

    parser.add_argument('-d', '--deactivate', '--logout',
                        dest="logout",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Send a logout request to end your privileged "
                             "session.")


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
    runs.set_defaults(func=cmd_line_client.handle_list_runs)
    __add_common_arguments(runs, has_matrix_output=True)

    results = subcommands.add_parser(
        'results',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Show the individual analysis reports' summary.",
        help="List analysis result (finding) summary for a given run.")
    __register_results(results)
    results.set_defaults(func=cmd_line_client.handle_list_results)
    __add_common_arguments(results, has_matrix_output=True)

    diff = subcommands.add_parser(
        'diff',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Compare two analysis runs to show the results that "
                    "differ between the two.",
        help="Compare two analysis runs and show the difference.")
    __register_diff(diff)
    diff.set_defaults(func=cmd_line_client.handle_diff_results)
    __add_common_arguments(diff, has_matrix_output=True)

    sum_p = subcommands.add_parser(
        'sum',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Show the count of checker reports per checker for some "
                    "analysis runs.",
        help="Show number of reports per checker.")
    __register_sum(sum_p)
    sum_p.set_defaults(func=cmd_line_client.handle_list_result_types)
    __add_common_arguments(sum_p, has_matrix_output=True)

    del_p = subcommands.add_parser(
        'del',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Remove analysis runs from the server based on some "
                    "criteria. NOTE! When a run is deleted, ALL associated "
                    "information is permanently lost!",
        help="Delete analysis runs.")
    __register_delete(del_p)
    del_p.set_defaults(func=cmd_line_client.handle_remove_run_results)
    __add_common_arguments(del_p)

    suppress = subcommands.add_parser(
        'suppress',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Exports or imports suppressions from a CodeChecker "
                    "server from/to a suppress file, and is also used (if "
                    "'--bugid' is specified) to (un)suppress reports.",
        help="Manage and export/import suppressions of a CodeChecker server.")
    __register_suppress(suppress)
    suppress.set_defaults(func=cmd_line_client.handle_suppress)
    __add_common_arguments(suppress)

    login = subcommands.add_parser(
        'login',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Certain CodeChecker servers can require elevated "
                    "privileges to access analysis results. In such cases "
                    "it is mandatory to authenticate to the server. This "
                    "action is used to perform an authentication in the "
                    "command-line.",
        help="Authenticate into CodeChecker servers that require privileges.")
    __register_auth(login)
    login.set_defaults(func=cmd_line_client.handle_login)
    __add_common_arguments(login)

# 'cmd' does not have a main() method in itself, as individual subcommands are
# handled later on separately.
