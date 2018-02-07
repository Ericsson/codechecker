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
import sys

from libcodechecker import logger
from libcodechecker import output_formatters
from libcodechecker import util
from libcodechecker.cmd import cmd_line_client
from libcodechecker.cmd import product_client


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


def __add_common_arguments(parser,
                           needs_product_url=True,
                           has_matrix_output=False):
    """
    Add some common arguments, like server address and verbosity, to parser.
    """

    common_group = parser.add_argument_group('common arguments')

    if needs_product_url is None:
        # Explicitly not add anything, the command does not connect to a
        # server.
        pass
    elif needs_product_url:
        # Command connects to a product on a server.
        common_group.add_argument('--url',
                                  type=str,
                                  metavar='PRODUCT_URL',
                                  dest="product_url",
                                  default="localhost:8001/Default",
                                  required=False,
                                  help="The URL of the product which will be "
                                       "accessed by the client, in the "
                                       "format of"
                                       " '[http[s]://]host:port/Endpoint'.")
    else:
        # Command connects to a server directly.
        common_group.add_argument('--url',
                                  type=str,
                                  metavar='SERVER_URL',
                                  dest="server_url",
                                  default="localhost:8001",
                                  required=False,
                                  help="The URL of the server to access, "
                                       "in the format of"
                                       " '[http[s]://]host:port'.")

    if has_matrix_output:
        common_group.add_argument('-o', '--output',
                                  dest="output_format",
                                  required=False,
                                  # TODO: 'plaintext' only kept for legacy.
                                  default="plaintext",
                                  choices=["plaintext", "html"] +
                                          output_formatters.USER_FORMATS,
                                  help="The output format to use in showing "
                                       "the data.")

        common_group.add_argument('-e', '--export-dir',
                                  dest="export_dir",
                                  default=argparse.SUPPRESS,
                                  help="Store the output in the given folder.")

        common_group.add_argument('-c', '--clean',
                                  dest="clean",
                                  required=False,
                                  action='store_true',
                                  default=argparse.SUPPRESS,
                                  help="Delete output results stored in the "
                                       "output directory. (By default, it "
                                       "would keep output files and "
                                       "overwrites only those that contain "
                                       "any reports).")

    logger.add_verbose_arguments(common_group)


def __add_filtering_arguments(parser):
    """
    Add some common filtering arguments to the given parser.
    """

    parser.add_argument('-s', '--suppressed',
                        dest="suppressed",
                        action='store_true',
                        help="DEPRECATED. Use the '--filter' option to get "
                             "false positive (suppressed) results. Show only "
                             "suppressed results instead of only unsuppressed "
                             "ones.")

    parser.add_argument('--filter',
                        type=str,
                        dest='filter',
                        default="::::",
                        help="Filter results. The filter string has the "
                             "following format: "
                             "[<SEVERITY>]:[<CHECKER_NAME>]:[<FILE_PATH>]:"
                             "[<DETECTION_STATUS>]:[<REVIEW_STATUS>]"
                             "where severity, checker_name, "
                             "file_path, detection_status, review_status "
                             "should be a comma separated list, e.g.:"
                             "\"high,medium:unix,core:*.cpp,*.h:"
                             "new,unresolved:false_positive,intentional\"")


def __register_results(parser):
    """
    Add argparse subcommand parser for the "list analysis results" action.
    """

    parser.add_argument(type=str,
                        dest="name",
                        metavar='RUN_NAMES',
                        help="Names of the analysis runs to show result "
                             "summaries of. This has the following format: "
                             "<run_name_1>:<run_name_2>:<run_name_3> "
                             "where run names can be a Python regex "
                             "expression. So if you have run_1_a_name, "
                             "run_2_b_name, run_2_c_name, run_3_d_name then"
                             "\"run_2*:run_3_d_name\" selects the last three"
                             "runs. Use 'CodeChecker cmd runs' to get the "
                             "available runs.")

    __add_filtering_arguments(parser)


def __register_diff(parser):
    """
    Add argparse subcommand parser for the "diff results" action.
    """

    parser.add_argument('-b', '--basename',
                        type=str,
                        dest="basename",
                        metavar='BASE_RUN',
                        required=True,
                        default=argparse.SUPPRESS,
                        help="The 'base' (left) side of the difference: this "
                             "analysis run is used as the initial state in "
                             "the comparison. The basename can be a Python "
                             "regex which is meant to cover the whole run "
                             "name. So if you have run_1_a_name, run_2_b_name "
                             "and run_2_c_name then run_.*_[ab]_name selects "
                             "the first two.")

    parser.add_argument('-n', '--newname',
                        type=str,
                        dest="newname",
                        metavar='NEW_RUN',
                        required=True,
                        default=argparse.SUPPRESS,
                        help="The 'new' (right) side of the difference: this "
                             "analysis run is compared to the -b/--basename "
                             "run. The parameter can be a run name"
                             "(on the remote server) or a local "
                             "report directory "
                             "(result of the analyze command)."
                        )

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
                                 "<run_name_3> where run names can be a "
                                 "Python regex expression. So if you have "
                                 "run_1_a_name, run_2_b_name, run_2_c_name, "
                                 "run_3_d_name then \"run_2*:run_3_d_name\""
                                 "selects the last three runs. Use "
                                 "'CodeChecker cmd runs' to get the available "
                                 "runs.")

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
                           needs_product_url=False, has_matrix_output=True)

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
    __add_common_arguments(diff, has_matrix_output=True)

    sum_p = subcommands.add_parser(
        'sum',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Show checker statistics for some analysis runs.",
        help="Show statistics of checkers.")
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

# 'cmd' does not have a main() method in itself, as individual subcommands are
# handled later on separately.
