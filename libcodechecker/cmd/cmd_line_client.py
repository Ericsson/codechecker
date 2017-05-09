# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from datetime import datetime
import getpass
import json
import sys

from thrift.Thrift import TApplicationException

import codeCheckerDBAccess
import shared
from Authentication import ttypes as AuthTypes

from libcodechecker import session_manager
from libcodechecker import suppress_file_handler
from libcodechecker.output_formatters import twodim_to_str

from . import thrift_helper
from . import authentication_helper

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

    auth_token = session.getToken(args.host, args.port)

    auth_client = authentication_helper.ThriftAuthHelper(args.host,
                                                         args.port,
                                                         '/Authentication',
                                                         auth_token)
    try:
        handshake = auth_client.getAuthParameters()

        if not handshake.requiresAuthentication:
            print("This server does not require privileged access.")
            return

        if auth_token and handshake.sessionStillActive:
            print("Active authentication token found no new login required.")
            return
        else:
            print("No/Old authentication token found please login again.")

    except TApplicationException:
        print("This server does not support privileged access.")
        return

    if 'logout' in args:
        logout_done = auth_client.destroySession()
        if logout_done:
            session.saveToken(args.host, args.port, None, True)
            print('Successfully deauthenticated from server.')
        return

    methods = auth_client.getAcceptedAuthMethods()
    # Attempt username-password auth first
    if 'Username:Password' in str(methods):
        pwd = None
        username = args.username

        # Try to use a previously saved credential from configuration file
        savedAuth = session.getAuthString(args.host, args.port)

        if savedAuth:
            print('Logging in using preconfigured credentials.')
            username = savedAuth.split(":")[0]
            pwd = savedAuth.split(":")[1]
        else:
            print('Logging in using command line credentials.')
            print('Please provide password for user: ' + username)
            pwd = getpass.getpass('Password:')

        print("Trying to login: " + username + "@" +
              args.host + ":" + args.port)
        try:
            session_token = auth_client.performLogin("Username:Password",
                                                     username + ":" +
                                                     pwd)

            session.saveToken(args.host, args.port, session_token)
            print("Server reported successful authentication!")
        except shared.ttypes.RequestFailed as reqfail:
            print("Authentication failed please check your credentials.")
            print(reqfail.message)
            sys.exit(1)
    else:
        print('Username, password authentication is not supported.')
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
        for name, _ in run_info.items():
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
        report_filter.severity\
            = shared.ttypes.Severity._NAMES_TO_VALUES[severity.upper()]
    if checker:
        report_filter.checkerId = '*' + checker + '*'
    if path:
        report_filter.filepath = path


# ---------------------------------------------------------------------------
# Argument handlers for the 'CodeChecker cmd' subcommands.
# ---------------------------------------------------------------------------

def handle_list_runs(args):
    client = setupClient(args.host, args.port, '/')
    runs = client.getRunData()

    if args.output_format == 'json':
        results = []
        for run in runs:
            results.append({run.name: run})
        print(CmdLineOutputEncoder().encode(results))

    else:  # plaintext, csv
        header = ['Name', 'ResultCount', 'RunDate']
        rows = []
        for run in runs:
            rows.append((run.name, str(run.resultCount), run.runDate))

        print(twodim_to_str(args.output_format, header, rows))


def handle_list_results(args):
    client = setupClient(args.host, args.port, '/')

    run_info = check_run_names(client, [args.name])

    run_id, _ = run_info.get(args.name)

    limit = codeCheckerDBAccess.constants.MAX_QUERY_SIZE
    offset = 0

    filters = []
    if args.suppressed:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(
            suppressed=True)
    else:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(
            suppressed=False)

    add_filter_conditions(report_filter, args.filter)
    filters.append(report_filter)

    all_results = []
    results = client.getRunResults(run_id, limit, offset, None, filters)

    while results:
        all_results.extend(results)
        offset += limit
        results = client.getRunResults(run_id, limit, offset, None,
                                       filters)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(all_results))
    else:

        if args.suppressed:
            header = ['File', 'Checker', 'Severity', 'Msg', 'Suppress comment']
        else:
            header = ['File', 'Checker', 'Severity', 'Msg']

        rows = []
        for res in all_results:
            bug_line = res.lastBugPosition.startLine
            checked_file = res.checkedFile + ' @ ' + str(bug_line)
            sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]

            if args.suppressed:
                rows.append((checked_file, res.checkerId, sev,
                             res.checkerMsg, res.suppressComment))
            else:
                rows.append(
                    (checked_file, res.checkerId, sev, res.checkerMsg))

        print(twodim_to_str(args.output_format, header, rows))


def handle_list_result_types(args):
    client = setupClient(args.host, args.port, '/')

    filters = []
    if args.suppressed:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(
            suppressed=True)
    else:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(
            suppressed=False)

    add_filter_conditions(report_filter, args.filter)
    filters.append(report_filter)

    if 'all_results' in args:
        items = check_run_names(client, None).items()
    else:
        items = []
        run_info = check_run_names(client, args.names)
        for name in args.names:
            items.append((name, run_info.get(name)))

    results_collector = []
    for name, run_info in items:
        run_id, run_date = run_info
        results = client.getRunResultTypes(run_id, filters)

        if args.output_format == 'json':
            for res in results:
                res.severity =\
                    shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
            results_collector.append({name: results})
        else:  # plaintext, csv
            print('Check date: ' + run_date)
            print('Check name: ' + name)
            rows = []
            header = ['Checker', 'Severity', 'Count']
            for res in results:
                sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                rows.append((res.checkerId, sev, str(res.count)))

            print(twodim_to_str(args.output_format, header, rows))

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(results_collector))


def handle_remove_run_results(args):
    client = setupClient(args.host, args.port, '/')

    def is_later(d1, d2):
        dateformat = '%Y-%m-%d %H:%M:%S.%f'

        if not isinstance(d1, datetime):
            d1 = datetime.strptime(d1, dateformat)
        if not isinstance(d2, datetime):
            d2 = datetime.strptime(d2, dateformat)

        return d1 > d2

    run_info = get_run_ids(client)

    if 'name' in args:
        check_run_names(client, args.name)

        def condition(name, runid, date):
            return name in args.name
    elif 'all_after_run' in args and args.all_after_run in run_info:
        run_date = run_info[args.all_after_run][1]

        def condition(name, runid, date):
            return is_later(date, run_date)
    elif 'all_before_run' in args and args.all_before_run in run_info:
        run_date = run_info[args.all_before_run][1]

        def condition(name, runid, date):
            return is_later(run_date, date)
    elif 'all_after_time' in args:
        def condition(name, runid, date):
            return is_later(date, args.all_after_time)
    elif 'all_before_time' in args:
        def condition(name, runid, date):
            return is_later(args.all_before_time, date)
    else:
        def condition(name, runid, date):
            return False

    client.removeRunResults([runid for (name, (runid, date))
                            in run_info.items()
                            if condition(name, runid, date)])

    print('Done.')


def handle_diff_results(args):
    def printResult(getterFn, baseid, newid, suppr, output_format):
        report_filter = [
            codeCheckerDBAccess.ttypes.ReportFilter(suppressed=suppr)]
        add_filter_conditions(report_filter[0], args.filter)

        sort_type = None
        limit = codeCheckerDBAccess.constants.MAX_QUERY_SIZE
        offset = 0

        all_results = []
        results = getterFn(baseid, newid, limit, offset, sort_type,
                           report_filter)

        while results:
            all_results.extend(results)
            offset += limit
            results = getterFn(baseid, newid, limit, offset, sort_type,
                               report_filter)

        if output_format == 'json':
            print(CmdLineOutputEncoder().encode(all_results))
        else:
            header = ['File', 'Checker', 'Severity', 'Msg']
            rows = []
            for res in all_results:
                bug_line = res.lastBugPosition.startLine
                sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                checked_file = res.checkedFile + ' @ ' + str(bug_line)
                rows.append(
                    (checked_file, res.checkerId, sev, res.checkerMsg))

            print(twodim_to_str(output_format, header, rows))

    client = setupClient(args.host, args.port, '/')
    run_info = check_run_names(client, [args.basename, args.newname])

    baseid = run_info[args.basename][0]
    newid = run_info[args.newname][0]

    if 'new' in args:
        printResult(client.getNewResults, baseid, newid, args.suppressed,
                    args.output_format)
    elif 'unresolved' in args:
        printResult(client.getUnresolvedResults, baseid, newid,
                    args.suppressed, args.output_format)
    elif 'resolved' in args:
        printResult(client.getResolvedResults, baseid, newid, args.suppressed,
                    args.output_format)


def handle_suppress(args):
    def update_suppression_comment(run_id, report_id, comment):
        client.unSuppressBug([run_id], report_id)
        client.suppressBug([run_id], report_id, comment)

    def bug_hash_filter(bug_id, filepath):
        filepath = '%' + filepath
        return [
            codeCheckerDBAccess.ttypes.ReportFilter(bugHash=bug_id,
                                                    suppressed=True,
                                                    filepath=filepath),
            codeCheckerDBAccess.ttypes.ReportFilter(bugHash=bug_id,
                                                    suppressed=False,
                                                    filepath=filepath)]

    already_suppressed = 'Bug {} in file {} already suppressed. Use --force!'
    limit = codeCheckerDBAccess.constants.MAX_QUERY_SIZE

    client = setupClient(args.host, args.port, '/')

    run_info = check_run_names(client, [args.name])
    run_id, run_date = run_info.get(args.name)

    if 'output' in args:
        for suppression in client.getSuppressedBugs(run_id):
            suppress_file_handler.write_to_suppress_file(
                args.output,
                suppression.bug_hash,
                suppression.file_name,
                suppression.comment)

    elif 'input' in args:
        with open(args.input) as supp_file:
            suppress_data = suppress_file_handler.get_suppress_data(supp_file)

        for bug_id, file_name, comment in suppress_data:
            reports = client.getRunResults(run_id, limit, 0, None,
                                           bug_hash_filter(bug_id, file_name))

            for report in reports:
                if report.suppressed and 'force' not in args:
                    print(already_suppressed.format(bug_id, file_name))
                else:
                    update_suppression_comment(
                        run_id, report.reportId, comment)

    elif 'bugid' in args:
        reports = client.getRunResults(run_id, limit, 0, None,
                                       bug_hash_filter(args.bugid,
                                                       args.file if 'file'
                                                       in args else ""))

        for report in reports:
            if 'unsuppress' in args:
                client.unSuppressBug([run_id], report.reportId)
            elif report.suppressed and 'force' not in args:
                print(already_suppressed.format(args.bugid,
                                                args.file if 'file' in args
                                                else ""))
            else:
                update_suppression_comment(run_id,
                                           report.reportId,
                                           args.comment if 'comment' in args
                                           else "")

