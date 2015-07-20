# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import sys
import argparse
import json
import operator

import thrift_helper

import shared
import codeCheckerDBAccess

SUPPORTED_VERSION = '3.0'


# ------------------------------------------------------------
def check_API_version(client):
    ''' check if server API is supported by the client'''
    version = client.getAPIVersion()
    supp_major_version = SUPPORTED_VERSION.split('.')[0]
    api_major_version = version.split('.')[0]

    if supp_major_version != api_major_version:
        return False

    return True

# ------------------------------------------------------------
class CmdLineOutputEncoder(json.JSONEncoder):

    def default(self, obj):
        d = {}
        d.update(obj.__dict__)
        return d

# ------------------------------------------------------------
def setupClient(host, port, uri):
    ''' setup the thrift client and check API version'''

    client = thrift_helper.ThriftClientHelper(host, port, uri)
    #test if client can work with thrift API getVersion
    if not check_API_version(client):
        print('Backward incompatible change was in the API.')
        print('Please update client. Server version is not supported')
        sys.exit(1)

    return client

# ------------------------------------------------------------
def print_table(lines, separate_head=True):
      """Prints a formatted table given a 2 dimensional array"""
      #Count the column width

      widths = []
      for line in lines:
          for i,size in enumerate([len(x) for x in line]):
              while i >= len(widths):
                  widths.append(0)
              if size > widths[i]:
                  widths[i] = size

      #Generate the format string to pad the columns
      print_string = ""
      for i,width in enumerate(widths):
          print_string += "{" + str(i) + ":" + str(width) + "} | "
      if (len(print_string) == 0):
          return
      print_string = print_string[:-3]

      #Print the actual data
      print("-"*(sum(widths)+3*(len(widths)-1)))
      for i,line in enumerate(lines):
          print(print_string.format(*line))
          if (i == 0 and separate_head):
              print("-"*(sum(widths)+3*(len(widths)-1)))
      print("-"*(sum(widths)+3*(len(widths)-1)))
      print ''

# ------------------------------------------------------------
def get_run_ids(client):
    ''' returns a map for run names and run_ids '''

    runs = client.getRunData()

    run_data = {}
    for run in runs:
        run_data[run.name] = (run.runId, run.runDate)

    return run_data


# ------------------------------------------------------------
def check_run_names(client, check_names):

    run_info = get_run_ids(client)

    if not check_names:
        return run_info

    missing_name = False
    for name in check_names:
        if not run_info.get(name):
            print('No check name found: ' +name)
            missing_name = True

    if missing_name:
        print('Possible check names are:')
        for name, info in run_info.items():
            print(name)
        sys.exit(1)

    return run_info


# ------------------------------------------------------------
def handle_list_runs(args):

    client = setupClient(args.host, args.port, '/')
    runs = client.getRunData()

    if args.output_format == 'json':
        results = []
        for run in runs:
            results.append({run.name : run})
        print CmdLineOutputEncoder().encode(results)

    else:
        rows = []
        rows.append(('Name', 'ResultCount', 'RunDate'))
        for run in runs:
            rows.append((run.name, str(run.resultCount), run.runDate))

        print_table(rows)


# ------------------------------------------------------------
def handle_list_results(args):

    client = setupClient(args.host, args.port, '/')

    run_info = check_run_names(client, [args.name])

    #for name, info in run_info.items()
    run_id, run_date = run_info.get(args.name)

    limit = 500
    offset = 0

    filters = []
    if args.suppressed:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(suppressed=True)
    else:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(suppressed=False)

    filters.append(report_filter)


    results = client.getRunResults(run_id, limit, offset, None, filters)

    if args.output_format == 'json':
        print CmdLineOutputEncoder().encode(results)
    else:
        rows = []
        if args.suppressed:
            rows.append(('File', 'Checker', 'Severity', 'Msg', 'Suppress comment'))
            while results:
                for res in results:
                    bug_line = res.lastBugPosition.startLine
                    checked_file = res.checkedFile+' @ '+str(bug_line)
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    rows.append((checked_file, res.checkerId, sev, res.checkerMsg, res.suppressComment))

                offset += limit
                results = client.getRunResults(run_id, limit, offset, None, filters)

        else:
            rows.append(('File', 'Checker', 'Severity', 'Msg'))
            while results:
                for res in results:
                    bug_line = res.lastBugPosition.startLine
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    checked_file = res.checkedFile+' @ '+str(bug_line)
                    rows.append((checked_file, res.checkerId, sev, res.checkerMsg))

                offset += limit
                results = client.getRunResults(run_id, limit, offset, None, filters)


        print_table(rows)

# ------------------------------------------------------------
def handle_list_result_types(args):

    client = setupClient(args.host, args.port, '/')

    filters = []
    if args.suppressed:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(suppressed=True)
    else:
        report_filter = codeCheckerDBAccess.ttypes.ReportFilter(suppressed=False)

    filters.append(report_filter)


    if args.all_results:
        run_info = check_run_names(client, None)
        results_collector = []
        for name, run_info in run_info.items():
            run_id , run_date = run_info
            results = client.getRunResultTypes(run_id, filters)
            if args.output_format == 'json':
                results_collector.append({name : results})
            else:
                print('Check date: '+run_date)
                print('Check name: '+name)
                rows = []
                rows.append(('Checker', 'Severity', 'Count'))
                for res in results:
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    rows.append((res.checkerId, sev, str(res.count)))

                print_table(rows)

        if args.output_format == 'json':
            print CmdLineOutputEncoder().encode(results_collector)
    else:
        run_info = check_run_names(client, args.names)
        for name in args.names:
            run_id, run_date = run_info.get(name)

            results = client.getRunResultTypes(run_id, filters)
            if args.output_format == 'json':
                print CmdLineOutputEncoder().encode(results)
            else:
                print('Check date: '+run_date)
                print('Check name: '+name)
                rows = []
                rows.append(('Checker', 'Severity', 'Count'))
                for res in results:
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    rows.append((res.checkerId, sev, str(res.count)))

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

# ------------------------------------------------------------
def handle_diff_results(args):
    def printResult(getterFn, baseid, newid, suppr, output_format):
        report_filter = [codeCheckerDBAccess.ttypes.ReportFilter(suppressed=suppr)]
        rows, sort_type, limit, offset = [], None, 500, 0

        rows.append(('File', 'Checker', 'Severity', 'Msg'))
        results = getterFn(baseid, newid, limit, offset, sort_type, report_filter)

        if output_format == 'json':
            print CmdLineOutputEncoder().encode(results)
        else:
            while results:
                for res in results:
                    bug_line = res.lastBugPosition.startLine
                    sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                    checked_file = res.checkedFile+' @ '+str(bug_line)
                    rows.append((checked_file, res.checkerId, sev, res.checkerMsg))

                offset += limit
                results = getterFn(baseid, newid, limit, offset, sort_type, report_filter)

            print_table(rows)

    client = setupClient(args.host, args.port, '/')
    run_info = check_run_names(client, [args.basename, args.newname])

    baseid = run_info[args.basename][0]
    newid = run_info[args.newname][0]

    if args.new:
        printResult(client.getNewResults, baseid, newid, args.suppressed, args.output_format)
    elif args.unresolved:
        printResult(client.getUnresolvedResults, baseid, newid, args.suppressed, args.output_format)
    elif args.resolved:
        printResult(client.getResolvedResults, baseid, newid, args.suppressed, args.output_format)

# ------------------------------------------------------------
def register_client_command_line(argument_parser):
    ''' should be used to extend the already existing arguments
    extend the argument parser with extra commands'''

    subparsers = argument_parser.add_subparsers()

    # list runs
    listruns_parser = subparsers.add_parser('runs', help='Get the run data.')
    listruns_parser.add_argument('--host', type=str, dest="host", default='localhost',
                                help='Server host.')
    listruns_parser.add_argument('-p','--port', type=str, dest="port", default=11444,
                             required=True, help='Server port.')
    listruns_parser.add_argument('-o', choices=['plaintext', 'json'], default='plaintext', type=str, dest="output_format", help='Output format.')
    listruns_parser.set_defaults(func=handle_list_runs)


    #list results
    listresults_parser = subparsers.add_parser('results', help='List results.')
    listresults_parser.add_argument('--host', type=str, dest="host", default='localhost',
                                help='Server host.')
    listresults_parser.add_argument('-p','--port', type=str, dest="port", default=11444,
                             required=True, help='Server port.')
    listresults_parser.add_argument('-n','--name', type=str, dest="name", required=True,
                                help='Check name.')
    listresults_parser.add_argument('-s','--suppressed', action="store_true", dest="suppressed", help='Suppressed results.')
    listresults_parser.add_argument('-o', choices=['plaintext', 'json'], default='plaintext', type=str, dest="output_format", help='Output format.')
    listresults_parser.set_defaults(func=handle_list_results)

    #list diffs
    diff_parser = subparsers.add_parser('diff', help='Diff two run.')
    diff_parser.add_argument('--host', type=str, dest="host", default='localhost',
                             help='Server host.')
    diff_parser.add_argument('-p','--port', type=str, dest="port", default=11444,
                             required=True, help='Server port.')
    diff_parser.add_argument('-b','--basename', type=str, dest="basename", required=True,
                                help='Base name.')
    diff_parser.add_argument('-n','--newname', type=str, dest="newname", required=True,
                                help='New name.')
    diff_parser.add_argument('-s','--suppressed', action="store_true", dest="suppressed", default=False,
                                required=False, help='Show suppressed bugs.')
    diff_parser.add_argument('-o', choices=['plaintext', 'json'], default='plaintext', type=str, dest="output_format", help='Output format.')
    group = diff_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--new', action="store_true", dest="new", help="Show new results.")
    group.add_argument('--unresolved', action="store_true", dest="unresolved", help="Show unresolved results.")
    group.add_argument('--resolved', action="store_true", dest="resolved", help="Show resolved results.")
    diff_parser.set_defaults(func=handle_diff_results)

    #list resulttypes
    sum_parser = subparsers.add_parser('sum', help='Sum results.')
    sum_parser.add_argument('--host', type=str, dest="host", default='localhost',
                                help='Server host.')
    sum_parser.add_argument('-p','--port', type=str, dest="port", default=11444,
                             required=True, help='Server port.')
    name_group = sum_parser.add_mutually_exclusive_group(required=True)
    name_group.add_argument('-n','--name', nargs='+',type=str, dest="names", help='Check name.')
    name_group.add_argument('-a','--all', action='store_true', dest="all_results", help='All results.')

    sum_parser.add_argument('-s','--suppressed', action="store_true", dest="suppressed", help='Suppressed results.')
    sum_parser.add_argument('-o', choices=['plaintext', 'json'], default='plaintext', type=str, dest="output_format", help='Output format.')
    sum_parser.set_defaults(func=handle_list_result_types)


    #list resulttypes
    sum_parser = subparsers.add_parser('del', help='Remove run results.')
    sum_parser.add_argument('--host', type=str, dest="host", default='localhost',
                                help='Server host.')
    sum_parser.add_argument('-p','--port', type=str, dest="port", default=11444,
                             required=True, help='Server port.')
    sum_parser.add_argument('-n','--name', nargs='+', type=str, dest="name", required=True, help='Server port.')
    sum_parser.set_defaults(func=handle_remove_run_results)

# ------------------------------------------------------------
def main():


    parser = argparse.ArgumentParser(description='Simple command line client for codechecker.')

    register_client_command_line(parser)
    args = parser.parse_args()
    args.func(args)


# ------------------------------------------------------------
if __name__ == "__main__":
    main()


