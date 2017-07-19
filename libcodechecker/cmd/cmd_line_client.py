# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import base64
from datetime import datetime
import json
import os
import sys

import shared
import codeCheckerDBAccess
from codeCheckerDBAccess import ttypes

from libcodechecker import suppress_file_handler
from libcodechecker.analyze import plist_parser
from libcodechecker.libclient.client import handle_auth
from libcodechecker.libclient.client import setup_client
from libcodechecker.logger import LoggerFactory
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.report import Report

LOG = LoggerFactory.get_new_logger('CMD')


class CmdLineOutputEncoder(json.JSONEncoder):
    def default(self, obj):
        d = {}
        d.update(obj.__dict__)
        return d


def get_run_ids(client):
    """
    Returns a map for run names and run_ids.
    """

    runs = client.getRunData(None)

    run_data = {}
    for run in runs:
        run_data[run.name] = (run.runId, run.runDate)

    return run_data


def check_run_names(client, check_names):
    """
    Check if the given names are valid runs on the server.
    """
    run_info = get_run_ids(client)

    if not check_names:
        return run_info

    missing_name = False
    for name in check_names:
        if not run_info.get(name):
            LOG.warning("The run named '" + name + "' was not found.")
            missing_name = True

    if missing_name:
        print("Possible run names are:")
        for name, _ in run_info.items():
            print(name)
        sys.exit(1)

    return run_info


def add_filter_conditions(report_filter, filter_str):
    """
    This function fills some attributes of the given report filter based on
    the filter string which is provided in the command line. The filter string
    has to contain three parts divided by colons: the severity, checker id and
    the file path respectively. The file path can contain joker characters, and
    the checker id doesn't have to be complete (e.g. unix).
    """

    if filter_str.count(':') != 2:
        LOG.error("Filter string has to contain two colons (e.g. "
                  "\":unix:*.cpp\").")
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
    client = setup_client(args.product_url)
    runs = client.getRunData(None)

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
    client = setup_client(args.product_url)

    run_info = check_run_names(client, [args.name])

    run_id, _ = run_info.get(args.name)

    limit = codeCheckerDBAccess.constants.MAX_QUERY_SIZE
    offset = 0

    filters = []
    report_filter = codeCheckerDBAccess.ttypes.ReportFilter()

    add_filter_conditions(report_filter, args.filter)
    filters.append(report_filter)

    all_results = []
    results = client.getRunResults([run_id], limit, offset, None, filters)

    while results:
        all_results.extend(results)
        offset += limit
        results = client.getRunResults([run_id], limit, offset, None,
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
            bug_line = res.line
            checked_file = res.checkedFile + ' @ ' + str(bug_line)
            sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]

            if args.suppressed:
                rows.append((checked_file, res.checkerId, sev,
                             res.checkerMsg, res.suppressComment))
            else:
                rows.append(
                    (checked_file, res.checkerId, sev, res.checkerMsg))

        print(twodim_to_str(args.output_format, header, rows))


def handle_diff_results(args):
    def getDiffResults(getterFn, baseid, newid):
        report_filter = [
            codeCheckerDBAccess.ttypes.ReportFilter()]
        add_filter_conditions(report_filter[0], args.filter)
        sort_mode = [(ttypes.SortMode(
            ttypes.SortType.FILENAME,
            ttypes.Order.ASC))]
        limit = codeCheckerDBAccess.constants.MAX_QUERY_SIZE
        offset = 0

        all_results = []
        results = getterFn(baseid, newid, limit, offset, sort_mode,
                           report_filter)

        while results:
            all_results.extend(results)
            offset += limit
            results = getterFn(baseid, newid, limit, offset, sort_mode,
                               report_filter)
        return all_results

    def getReportDirResults(reportdir):
        all_reports = []
        for filename in os.listdir(reportdir):
            if filename.endswith(".plist"):
                file_path = os.path.join(reportdir, filename)
                LOG.debug("Parsing:" + file_path)
                try:
                    files, reports = plist_parser.parse_plist(file_path)
                    for report in reports:
                        report.main['location']['file_name'] = \
                            files[int(report.main['location']['file'])]
                    all_reports.extend(reports)

                except Exception as ex:
                    LOG.error('The generated plist is not valid!')
                    LOG.error(ex)
        return all_reports

    def getLineFromFile(filename, lineno):
        with open(filename, 'r') as f:
            i = 1
            for line in f:
                if i == lineno:
                    return line
                i += 1
        return ""

    def getLineFromRemoteFile(client, fid, lineno):
        # Thrift Python client cannot decode JSONs that contain non '\u00??'
        # characters, so we instead ask for a Base64-encoded version.
        source = client.getSourceFileData(fid, True, ttypes.Encoding.BASE64)
        lines = base64.b64decode(source.fileContent).split('\n')
        return "" if len(lines) < lineno else lines[lineno - 1]

    def getDiffReportDir(getterFn, baseid, report_dir, diff_type):
        report_filter = [
            codeCheckerDBAccess.ttypes.ReportFilter()]
        add_filter_conditions(report_filter[0], args.filter)

        sort_mode = [(ttypes.SortMode(
            ttypes.SortType.FILENAME,
            ttypes.Order.ASC))]
        limit = codeCheckerDBAccess.constants.MAX_QUERY_SIZE
        offset = 0

        base_results = []
        results = getterFn(baseid, limit, offset, sort_mode,
                           report_filter)
        while results:
            base_results.extend(results)
            offset += limit
            results = getterFn(baseid, limit, offset, sort_mode,
                               report_filter)
        base_hashes = {}
        for res in base_results:
            base_hashes[res.bugHash] = res

        filtered_reports = []
        new_results = getReportDirResults(report_dir)
        new_hashes = {}
        for rep in new_results:
            bughash = rep.main['issue_hash_content_of_line_in_context']
            new_hashes[bughash] = rep
        if diff_type == 'new':
            # Shows new reports from the report dir
            # which are not present in the baseline (server).
            for result in new_results:
                if not (result.main['issue_hash_content_of_line_in_context']
                        in base_hashes):
                    filtered_reports.append(result)
        elif diff_type == 'resolved':
            # Show bugs in the baseline (server)
            # which are not present in the report dir.
            for result in base_results:
                if not (result.bugHash in new_hashes):
                    filtered_reports.append(result)
        elif diff_type == 'unresolved':
            # Shows bugs in the report dir
            # which are also present in the baseline (server).
            for result in new_results:
                new_hash = result.main['issue_hash_content_of_line_in_context']
                if new_hash in base_hashes:
                    filtered_reports.append(result)
        return filtered_reports

    def printReports(client, reports, output_format):
        if output_format == 'json':
            output = []
            for report in reports:
                if type(report) is Report:
                    output.append(report.main)
                else:
                    output.append(report)
            print(CmdLineOutputEncoder().encode(output))
            return

        header = ['File', 'Checker', 'Severity', 'Msg', 'Source']
        rows = []
        for report in reports:
            if type(report) is Report:
                bug_line = report.main['location']['line']
                bug_col = report.main['location']['col']
                sev = 'unknown'
                checked_file = report.main['location']['file_name']\
                    + ':' + str(bug_line) + ":" + str(bug_col)
                check_name = report.main['check_name']
                check_msg = report.main['description']
                source_line =\
                    getLineFromFile(report.main['location']['file_name'],
                                    bug_line)
            else:
                bug_line = report.line
                bug_col = report.column
                sev = \
                    shared.ttypes.Severity._VALUES_TO_NAMES[report.severity]
                checked_file = report.checkedFile + ':' + str(bug_line) +\
                    ":" + str(bug_col)
                source_line =\
                    getLineFromRemoteFile(client, report.fileId, bug_line)
                check_name = report.checkerId
                check_msg = report.checkerMsg
            rows.append(
                (checked_file, check_name, sev, check_msg, source_line))
        if output_format == 'plaintext':
            for row in rows:
                print("{0}: {1} [{2}]\n{3}\n".format(row[0],
                      row[3], row[1], row[4]))
        else:
            print(twodim_to_str(output_format, header, rows))

    client = setup_client(args.product_url)

    report_dir_mode = False
    if os.path.isdir(args.newname):
        # If newname is a valid directory
        # we assume that it is a report dir
        # and we are in local compare mode.
        run_info = check_run_names(client, [args.basename])
        report_dir_mode = True
    else:
        run_info = check_run_names(client, [args.basename, args.newname])
        newid = run_info[args.newname][0]

    baseid = run_info[args.basename][0]
    results = []
    if report_dir_mode:
        diff_type = 'new'
        if 'unresolved' in args:
            diff_type = 'unresolved'
        elif 'resolved' in args:
            diff_type = 'resolved'
        results = getDiffReportDir(client.getRunResults, [baseid],
                                   os.path.abspath(args.newname), diff_type)
    else:
        if 'new' in args:
            results = getDiffResults(client.getNewResults, baseid, newid)
        elif 'unresolved' in args:
            results = getDiffResults(client.getUnresolvedResults,
                                     baseid, newid)
        elif 'resolved' in args:
            results = getDiffResults(client.getResolvedResults, baseid, newid)

    printReports(client, results, args.output_format)


def handle_list_result_types(args):
    client = setup_client(args.product_url)

    filters = []
    report_filter = codeCheckerDBAccess.ttypes.ReportFilter()

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
            print("Run '" + name + "', executed at '" + run_date + "'")
            rows = []
            header = ['Checker', 'Severity', 'Count']
            for res in results:
                sev = shared.ttypes.Severity._VALUES_TO_NAMES[res.severity]
                rows.append((res.checkerId, sev, str(res.count)))

            print(twodim_to_str(args.output_format, header, rows))

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(results_collector))


def handle_remove_run_results(args):
    client = setup_client(args.product_url)

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

    LOG.info("Done.")


def handle_suppress(args):
    def bug_hash_filter(bug_id, filepath):
        filepath = '%' + filepath
        return [
            codeCheckerDBAccess.ttypes.ReportFilter(bugHash=bug_id,
                                                    filepath=filepath),
            codeCheckerDBAccess.ttypes.ReportFilter(bugHash=bug_id,
                                                    filepath=filepath)]

    limit = codeCheckerDBAccess.constants.MAX_QUERY_SIZE

    client = setup_client(args.product_url)

    run_info = check_run_names(client, [args.name])
    run_id, run_date = run_info.get(args.name)

    if 'input' in args:
        with open(args.input) as supp_file:
            suppress_data = suppress_file_handler.get_suppress_data(supp_file)

        for bug_id, file_name, comment in suppress_data:
            reports = client.getRunResults([run_id], limit, 0, None,
                                           bug_hash_filter(bug_id, file_name))

            for report in reports:
                status = shared.ttypes.ReviewStatus.FALSE_POSITIVE
                client.changeReviewStatus(report.reportId, status, comment)


def handle_login(args):
    handle_auth(args.host, args.port, args.username,
                login='logout' not in args)
