# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import argparse
import csv
import json
import sys

import codeCheckerDBAccess
import shared
from . import thrift_helper
from . import authentication_helper

from thrift.Thrift import TApplicationException
from Authentication import ttypes as AuthTypes

from codechecker_lib import session_manager
from codechecker_lib.util import print_table

SUPPORTED_VERSION = '5.0'


def check_API_version(client):
    """ Check if server API is supported by the client. """
    version = client.getAPIVersion()
    supp_major_version = SUPPORTED_VERSION.split('.')[0]
    api_major_version = version.split('.')[0]

    if supp_major_version != api_major_version:
        return False

    return True


class CmdLineOutputEncoder(json.JSONEncoder):
    def default(self, obj):
        d = {}
        d.update(obj.__dict__)
        return d

def handle_auth_requests(args):
    session = session_manager.SessionManager_Client()
    auth_client = authentication_helper.ThriftAuthHelper(args.host,
                                                         args.port,
                                                         '/Authentication',
                                                         session.getToken(
                                                             args.host,
                                                             args.port))

    try:
        handshake = auth_client.getAuthParameters()
    except TApplicationException as tex:
        print("This server does not support privileged access.")
        return

    if not handshake.requiresAuthentication:
        print("This server does not require privileged access.")
        return

    if args.logout:
        if args.username or args.password:
            print('ERROR! Do not supply username and password '
                  'with `--logout` command.')
            sys.exit(1)

        logout_done = auth_client.destroySession()
        if logout_done:
            session.saveToken(args.host, args.port, None, True)
            print('Successfully deauthenticated from server.')

        return

    methods = auth_client.getAcceptedAuthMethods()
    # Attempt username-password auth first
    if 'Username:Password' in str(methods):
        if not args.username or not args.password:
            # Try to use a previously saved credential from configuration file
            savedAuth = session.getAuthString(args.host, args.port)

            if savedAuth:
                print('Logging in using preconfigured credentials.')
                args.username = savedAuth.split(":")[0]
                args.password = savedAuth.split(":")[1]
            else:
                print('Can not authenticate with username'
                      'and password if it is not specified...')
                sys.exit(1)

        try:
            session_token = auth_client.performLogin("Username:Password",
                                                     args.username + ":" +
                                                     args.password)
            session.saveToken(args.host, args.port, session_token)
            print("Server reported successful authentication!")
        except shared.ttypes.RequestFailed as reqfail:
            print(reqfail.message)
            sys.exit(1)


def __check_authentication(client):
    """Communicate with the authentication server
    to handle authentication requests."""
    result = client.getAuthParameters()

    if result.sessionStillActive:
        return True
    else:
        return False

def setupClient(host, port, uri):
    ''' setup the thrift client and check
    API version and authentication needs. '''
    manager = session_manager.SessionManager_Client()
    session_token = manager.getToken(host, port)

    # Before actually communicating with the server,
    # we need to check authentication first
    auth_client = authentication_helper.ThriftAuthHelper(host,
                                                         port,
                                                         uri +
                                                         'Authentication',
                                                         session_token)
    try:
        auth_response = auth_client.getAuthParameters()
    except TApplicationException as tex:
        auth_response = AuthTypes.HandshakeInformation()
        auth_response.requiresAuthentication = False

    if auth_response.requiresAuthentication and \
            not auth_response.sessionStillActive:
        print_err = False

        if manager.is_autologin_enabled():
            auto_auth_string = manager.getAuthString(host, port)
            if auto_auth_string:
                # Try to automatically log in with a saved credential
                # if it exists for the server
                try:
                    session_token = auth_client.performLogin(
                        "Username:Password",
                        auto_auth_string)
                    manager.saveToken(host, port, session_token)
                    print("Authenticated using pre-configured credentials...")
                except shared.ttypes.RequestFailed:
                    print_err = True
        else:
            print_err = True

        if print_err:
            print('Access denied. This server requires authentication.')
            print('Please log in onto the server '
                  'using `CodeChecker cmd login`.')
            sys.exit(1)

    client = thrift_helper.ThriftClientHelper(host, port, uri, session_token)
    # test if client can work with thrift API getVersion
    if not check_API_version(client):
        print('Backward incompatible change was in the API.')
        print('Please update client. Server version is not supported.')
        sys.exit(1)

    return client


def get_run_ids(client):
    """ Returns a map for run names and run_ids. """

    runs = client.getRunData()

    run_data = {}
    for run in runs:
        run_data[run.name] = (run.runId, run.runDate)

    return run_data


def check_run_names(client, check_names):
    run_info = get_run_ids(client)

    if not check_names:
        return run_info

    missing_name = False
    for name in check_names:
        if not run_info.get(name):
            print('No check name found: ' + name)
            missing_name = True

    if missing_name:
        print('Possible check names are:')
        for name, info in run_info.items():
            print(name)
        sys.exit(1)

    return run_info

def add_filter_conditions(report_filter, filter_str):
    """This function fills some attributes of the given report filter based on
    the filter string which is provided in the command line. The filter string
    has to contain three parts divided by colons: the severity, checker id and
    the file path respectively. The file path can contain joker characters, and
    the checker id doesn't have to be complete (e.g. unix)."""

    if filter_str.count(':') != 2:
        print('Filter string has to contain two colons (e.g. ":unix:*.cpp").')
        sys.exit(1)

    severity, checker, path = map(lambda x: x.strip(), filter_str.split(':'))

    if severity:
        report_filter.severity = shared.ttypes.Severity._NAMES_TO_VALUES[severity.upper()]
    if checker:
        report_filter.checkerId = '*' + checker + '*'
    if path:
        report_filter.filepath = path

def handle_list_runs(args):
    client = setupClient(args.host, args.port, '/')
    runs = client.getRunData()

    if args.output_format == 'json':
        results = []
        for run in runs:
            results.append({run.name: run})
        print(CmdLineOutputEncoder().encode(results))

    else:  # plaintext, csv
        rows = [('Name', 'ResultCount', 'RunDate')]
        for run in runs:
            rows.append((run.name, str(run.resultCount), run.runDate))

        if args.output_format == 'csv':
            writer = csv.writer(sys.stdout)
            writer.writerows(rows)
        else:
            print_table(rows)


def handle_list_results(args):
    client = setupClient(args.host, args.port, '/')

    run_info = check_run_names(client, [args.name])

    run_id, run_date = run_info.get(args.name)

    limit = 500
    offset = 0

    filters = []
    if args.suppressed:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(suppressed=True)
    else:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(
            suppressed=False)

    add_filter_conditions(report_filter, args.filter)
    filters.append(report_filter)

    results = client.getRunResults(run_id, limit, offset, None, filters)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(results))
    else:  # plaintext, csv
        rows = []
        if args.suppressed:
            rows.append(
                ('File', 'Checker', 'Severity', 'Msg', 'Suppress comment'))
            while results:
                for res in results:
                    bug_line = res.lastBugPosition.startLine
                    checked_file = res.checkedFile + ' @ ' + str(bug_line)
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    rows.append((checked_file, res.checkerId, sev,
                                 res.checkerMsg, res.suppressComment))

                offset += limit
                results = client.getRunResults(run_id, limit, offset, None,
                                               filters)

        else:
            rows.append(('File', 'Checker', 'Severity', 'Msg'))
            while results:
                for res in results:
                    bug_line = res.lastBugPosition.startLine
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    checked_file = res.checkedFile + ' @ ' + str(bug_line)
                    rows.append(
                        (checked_file, res.checkerId, sev, res.checkerMsg))

                offset += limit
                results = client.getRunResults(run_id, limit, offset, None,
                                               filters)

        if args.output_format == 'csv':
            writer = csv.writer(sys.stdout)
            writer.writerows(rows)
        else:
            print_table(rows)


def handle_list_result_types(args):
    client = setupClient(args.host, args.port, '/')

    filters = []
    if args.suppressed:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(suppressed=True)
    else:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(
            suppressed=False)

    add_filter_conditions(report_filter, args.filter)
    filters.append(report_filter)

    if args.all_results:
        run_info = check_run_names(client, None)
        results_collector = []
        for name, run_info in run_info.items():
            run_id, run_date = run_info
            results = client.getRunResultTypes(run_id, filters)
            if args.output_format == 'json':
                results_collector.append({name: results})
            else:  # plaintext, csv
                print('Check date: ' + run_date)
                print('Check name: ' + name)
                rows = []
                rows.append(('Checker', 'Severity', 'Count'))
                for res in results:
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    rows.append((res.checkerId, sev, str(res.count)))

                if args.output_format == 'csv':
                    writer = csv.writer(sys.stdout)
                    writer.writerows(rows)
                else:
                    print_table(rows)

        if args.output_format == 'json':
            print(CmdLineOutputEncoder().encode(results_collector))
    else:
        run_info = check_run_names(client, args.names)
        for name in args.names:
            run_id, run_date = run_info.get(name)

            results = client.getRunResultTypes(run_id, filters)
            if args.output_format == 'json':
                print(CmdLineOutputEncoder().encode(results))
            else:  # plaintext, csv
                print('Check date: ' + run_date)
                print('Check name: ' + name)
                rows = [('Checker', 'Severity', 'Count')]
                for res in results:
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    rows.append((res.checkerId, sev, str(res.count)))

                if args.output_format == 'csv':
                    writer = csv.writer(sys.stdout)
                    writer.writerows(rows)
                else:
                    print_table(rows)


# ------------------------------------------------------------
def handle_remove_run_results(args):
    client = setupClient(args.host, args.port, '/')

    run_info = check_run_names(client, args.name)

    # FIXME LIST comprehension
    run_ids_to_delete = []
    for name, info in run_info.items():
        run_id, run_date = info
        if name in args.name:
            run_ids_to_delete.append(run_id)

    client.removeRunResults(run_ids_to_delete)

    print('Done.')


def handle_diff_results(args):
    def printResult(getterFn, baseid, newid, suppr, output_format):
        report_filter = [
            codeCheckerDBAccess.ttypes.ReportFilter(suppressed=suppr)]
        add_filter_conditions(report_filter[0], args.filter)
        rows, sort_type, limit, offset = [], None, 500, 0

        rows.append(('File', 'Checker', 'Severity', 'Msg'))
        results = getterFn(baseid, newid, limit, offset, sort_type,
                           report_filter)

        if output_format == 'json':
            print(CmdLineOutputEncoder().encode(results))
        else:  # plaintext, csv
            while results:
                for res in results:
                    bug_line = res.lastBugPosition.startLine
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    checked_file = res.checkedFile + ' @ ' + str(bug_line)
                    rows.append(
                        (checked_file, res.checkerId, sev, res.checkerMsg))

                offset += limit
                results = getterFn(baseid, newid, limit, offset, sort_type,
                                   report_filter)

            if output_format == 'csv':
                writer = csv.writer(sys.stdout)
                writer.writerows(rows)
            else:
                print_table(rows)

    client = setupClient(args.host, args.port, '/')
    run_info = check_run_names(client, [args.basename, args.newname])

    baseid = run_info[args.basename][0]
    newid = run_info[args.newname][0]

    if args.new:
        printResult(client.getNewResults, baseid, newid, args.suppressed,
                    args.output_format)
    elif args.unresolved:
        printResult(client.getUnresolvedResults, baseid, newid, args.suppressed,
                    args.output_format)
    elif args.resolved:
        printResult(client.getResolvedResults, baseid, newid, args.suppressed,
                    args.output_format)


def register_client_command_line(argument_parser):
    """ Should be used to extend the already existing arguments
    extend the argument parser with extra commands."""

    subparsers = argument_parser.add_subparsers()

    # List runs.
    listruns_parser = subparsers.add_parser('runs', help='Get the run data.')
    listruns_parser.add_argument('--host', type=str, dest="host",
                                 default='localhost',
                                 help='Server host.')
    listruns_parser.add_argument('-p', '--port', type=str, dest="port",
                                 default=11444,
                                 required=True, help='HTTP Server port.')
    listruns_parser.add_argument('-o', choices=['plaintext', 'json', 'csv'],
                                 default='plaintext', type=str,
                                 dest="output_format", help='Output format.')
    listruns_parser.set_defaults(func=handle_list_runs)

    # List results.
    listresults_parser = subparsers.add_parser('results', help='List results.')
    listresults_parser.add_argument('--host', type=str, dest="host",
                                    default='localhost',
                                    help='Server host.')
    listresults_parser.add_argument('-p', '--port', type=str, dest="port",
                                    default=11444,
                                    required=True, help='HTTP Server port.')
    listresults_parser.add_argument('-n', '--name', type=str, dest="name",
                                    required=True,
                                    help='Check name.')
    listresults_parser.add_argument('-s', '--suppressed', action="store_true",
                                    dest="suppressed",
                                    help='Suppressed results.')
    listresults_parser.add_argument('--filter', dest='filter', type=str,
                                    default='::', help='Filter string in the '\
                                    'following format: '\
                                    '<severity>:<checker_name>:<file_path>')
    listresults_parser.add_argument('-o', choices=['plaintext', 'json', 'csv'],
                                    default='plaintext', type=str,
                                    dest="output_format", help='Output format.')
    listresults_parser.set_defaults(func=handle_list_results)

    # List diffs.
    diff_parser = subparsers.add_parser('diff', help='Diff two run.')
    diff_parser.add_argument('--host', type=str, dest="host",
                             default='localhost',
                             help='Server host.')
    diff_parser.add_argument('-p', '--port', type=str, dest="port",
                             default=11444,
                             required=True, help='HTTP Server port.')
    diff_parser.add_argument('-b', '--basename', type=str, dest="basename",
                             required=True,
                             help='Base name.')
    diff_parser.add_argument('-n', '--newname', type=str, dest="newname",
                             required=True,
                             help='New name.')
    diff_parser.add_argument('-s', '--suppressed', action="store_true",
                             dest="suppressed", default=False,
                             required=False, help='Show suppressed bugs.')
    diff_parser.add_argument('-o', choices=['plaintext', 'json', 'csv'],
                             default='plaintext', type=str,
                             dest="output_format", help='Output format.')
    diff_parser.add_argument('--filter', dest='filter', type=str,
                             default='::', help='Filter string in the '\
                             'following format: '\
                             '<severity>:<checker_name>:<file_path>')
    group = diff_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--new', action="store_true", dest="new",
                       help="Show new results.")
    group.add_argument('--unresolved', action="store_true", dest="unresolved",
                       help="Show unresolved results.")
    group.add_argument('--resolved', action="store_true", dest="resolved",
                       help="Show resolved results.")
    diff_parser.set_defaults(func=handle_diff_results)

    # List resulttypes.
    sum_parser = subparsers.add_parser('sum', help='Sum results.')
    sum_parser.add_argument('--host', type=str, dest="host",
                            default='localhost',
                            help='Server host.')
    sum_parser.add_argument('-p', '--port', type=str, dest="port",
                            default=11444,
                            required=True, help='HTTP Server port.')
    name_group = sum_parser.add_mutually_exclusive_group(required=True)
    name_group.add_argument('-n', '--name', nargs='+', type=str, dest="names",
                            help='Check name.')
    name_group.add_argument('-a', '--all', action='store_true',
                            dest="all_results", help='All results.')

    sum_parser.add_argument('-s', '--suppressed', action="store_true",
                            dest="suppressed", help='Suppressed results.')
    sum_parser.add_argument('--filter', dest='filter', type=str,
                            default='::', help='Filter string in the '\
                            'following format: '\
                            '<severity>:<checker_name>:<source_file_path>')
    sum_parser.add_argument('-o', choices=['plaintext', 'json', 'csv'],
                            default='plaintext', type=str, dest="output_format",
                            help='Output format.')
    sum_parser.set_defaults(func=handle_list_result_types)

    # List resulttypes.
    sum_parser = subparsers.add_parser('del', help='Remove run results.')
    sum_parser.add_argument('--host', type=str, dest="host",
                            default='localhost',
                            help='Server host.')
    sum_parser.add_argument('-p', '--port', type=str, dest="port",
                            default=11444,
                            required=True, help='HTTP Server port.')
    sum_parser.add_argument('-n', '--name', nargs='+', type=str, dest="name",
                            required=True, help='Server port.')
    sum_parser.set_defaults(func=handle_remove_run_results)

    # Handle authentication.
    auth_parser = subparsers.add_parser('login', help='Log in onto a CodeChecker server.')
    auth_parser.add_argument('--host', type=str, dest="host", default='localhost',
                             help='Server host.')
    auth_parser.add_argument('-p', '--port', type=str, dest="port", default=11444,
                             required=True, help='HTTP Server port.')
    auth_parser.add_argument('-u', '--username', type=str, dest="username",
                             required=False, help='Username to use on authentication.')
    auth_parser.add_argument('-pw', '--password', type=str, dest="password",
                             required=False, help="Password for username-password authentication (optional).")
    auth_parser.add_argument('-d', '--deactivate', '--logout', action='store_true',
                             dest='logout', help='Send a logout request for the server.')
    auth_parser.set_defaults(func=handle_auth_requests)

def main():
    parser = argparse.ArgumentParser(
        description='Simple command line client for CodeChecker.')

    register_client_command_line(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
