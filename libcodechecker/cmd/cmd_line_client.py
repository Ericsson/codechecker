# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import base64
from datetime import datetime
import json
import os
import re
import sys

from codeCheckerDBAccess_v6 import constants, ttypes

from libcodechecker import suppress_handler
from libcodechecker import suppress_file_handler
from libcodechecker.analyze import plist_parser
from libcodechecker.libclient.client import handle_auth
from libcodechecker.libclient.client import setup_client
from libcodechecker.logger import LoggerFactory
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.report import Report
from libcodechecker.util import split_server_url


LOG = LoggerFactory.get_new_logger('CMD')


class CmdLineOutputEncoder(json.JSONEncoder):
    def default(self, obj):
        d = {}
        d.update(obj.__dict__)
        return d


def check_run_names(client, check_names):
    """
    Check if the given names are valid runs on the server. If any of the names
    is not found then the script finishes. Otherwise a dictionary returns which
    maps run names to runs. The dictionary contains only the runs in
    check_names or all runs if check_names is empty or None.
    """
    run_info = {run.name: run for run in client.getRunData(None)}

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
                  "\"high,medium:unix,core:*.cpp\").")
        sys.exit(1)

    severities, checkers, paths = map(lambda x: x.strip(),
                                      filter_str.split(':'))

    if severities:
        report_filter.severity = map(
                lambda x: ttypes.Severity._NAMES_TO_VALUES[x.upper()],
                severities.split(','))
    if checkers:
        report_filter.checkerName = map(lambda x: '*' + x + '*',
                                        checkers.split(','))
    if paths:
        report_filter.filepath = map(lambda x: '*' + x + '*',
                                     paths.split(','))

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

    run = run_info.get(args.name)

    limit = constants.MAX_QUERY_SIZE
    offset = 0

    report_filter = ttypes.ReportFilter()

    add_filter_conditions(report_filter, args.filter)

    all_results = []
    results = client.getRunResults([run.runId], limit, offset, None,
                                   report_filter, None)

    while results:
        all_results.extend(results)
        offset += limit
        results = client.getRunResults([run.runId], limit, offset, None,
                                       report_filter, None)

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
            sev = ttypes.Severity._VALUES_TO_NAMES[res.severity]

            if args.suppressed:
                rows.append((checked_file, res.checkerId, sev,
                             res.checkerMsg, res.suppressComment))
            else:
                rows.append(
                    (checked_file, res.checkerId, sev, res.checkerMsg))

        print(twodim_to_str(args.output_format, header, rows))


def handle_diff_results(args):

    def getDiffResults(client, baseids, cmp_data):

        report_filter = ttypes.ReportFilter()
        add_filter_conditions(report_filter, args.filter)

        # Do not show resolved bugs in compare mode new.
        if cmp_data.diffType == ttypes.DiffType.NEW:
            report_filter.detectionStatus = [
                ttypes.DetectionStatus.NEW,
                ttypes.DetectionStatus.UNRESOLVED,
                ttypes.DetectionStatus.REOPENED]

        sort_mode = [(ttypes.SortMode(
            ttypes.SortType.FILENAME,
            ttypes.Order.ASC))]
        limit = constants.MAX_QUERY_SIZE
        offset = 0

        all_results = []
        results = client.getRunResults(baseids,
                                       limit,
                                       offset,
                                       sort_mode,
                                       report_filter,
                                       cmp_data)

        while results:
            all_results.extend(results)
            offset += limit
            results = client.getRunResults(baseids,
                                           limit,
                                           offset,
                                           sort_mode,
                                           report_filter,
                                           cmp_data)
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

    def getDiffReportDir(client, baseids, report_dir, diff_type):

        report_filter = ttypes.ReportFilter()
        add_filter_conditions(report_filter, args.filter)

        sort_mode = [(ttypes.SortMode(
            ttypes.SortType.FILENAME,
            ttypes.Order.ASC))]
        limit = constants.MAX_QUERY_SIZE
        offset = 0

        base_results = []
        results = client.getRunResults(baseids,
                                       limit,
                                       offset,
                                       sort_mode,
                                       report_filter,
                                       None)
        while results:
            base_results.extend(results)
            offset += limit
            results = client.getRunResults(baseids,
                                           limit,
                                           offset,
                                           sort_mode,
                                           report_filter,
                                           None)
        base_hashes = {}
        for res in base_results:
            base_hashes[res.bugHash] = res

        filtered_reports = []
        new_results = getReportDirResults(report_dir)
        new_hashes = {}
        suppressed_in_code = []

        for rep in new_results:
            bughash = rep.main['issue_hash_content_of_line_in_context']
            source_file = rep.main['location']['file_name']
            bug_line = rep.main['location']['line']
            new_hashes[bughash] = rep
            sp_handler = suppress_handler.SourceSuppressHandler(
                    source_file,
                    bug_line,
                    bughash,
                    rep.main['check_name'])
            if sp_handler.get_suppressed():
                suppressed_in_code.append(bughash)
                LOG.debug("Bug " + bughash +
                          "is suppressed in code. file:" + source_file +
                          "Line "+str(bug_line))

        if diff_type == 'new':
            # Shows new reports from the report dir
            # which are not present in the baseline (server)
            # and not suppressed in the code.
            for result in new_results:
                if not (result.main['issue_hash_content_of_line_in_context']
                        in base_hashes) and\
                   not (result.main['issue_hash_content_of_line_in_context']
                        in suppressed_in_code):
                    filtered_reports.append(result)
        elif diff_type == 'resolved':
            # Show bugs in the baseline (server)
            # which are not present in the report dir
            # or suppressed.
            for result in base_results:
                if not (result.bugHash in new_hashes) or\
                        (result.bugHash in suppressed_in_code):
                    filtered_reports.append(result)
        elif diff_type == 'unresolved':
            # Shows bugs in the report dir
            # that are not suppressed and
            # which are also present in the baseline (server)

            for result in new_results:
                new_hash = result.main['issue_hash_content_of_line_in_context']
                if new_hash in base_hashes and\
                        not (new_hash in suppressed_in_code):
                    filtered_reports.append(result)
        return filtered_reports

    def printReports(client, reports, output_format):
        if output_format == 'json':
            output = []
            for report in reports:
                if isinstance(report, Report):
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
                sev = ttypes.Severity._VALUES_TO_NAMES[report.severity]
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
        # If newname is a valid directory we assume that it is a report dir and
        # we are in local compare mode.
        report_dir_mode = True
    else:
        run_info = check_run_names(client, [args.newname])
        newid = run_info[args.newname].runId

    try:
        basename_regex = '^' + args.basename + '$'
        base_runs = filter(lambda run: re.match(basename_regex, run.name),
                           client.getRunData(None))
        base_ids = map(lambda run: run.runId, base_runs)
    except re.error:
        LOG.error('Invalid regex format in ' + args.basename)
        sys.exit(1)

    if len(base_ids) == 0:
        LOG.warning("No run names match the given pattern: " + args.basename)
        sys.exit(1)

    LOG.info("Matching against runs: " +
             ', '.join(map(lambda run: run.name, base_runs)))

    results = []
    if report_dir_mode:
        diff_type = 'new'
        if 'unresolved' in args:
            diff_type = 'unresolved'
        elif 'resolved' in args:
            diff_type = 'resolved'
        results = getDiffReportDir(client, base_ids,
                                   os.path.abspath(args.newname),
                                   diff_type)
    else:
        cmp_data = ttypes.CompareData(runIds=[newid])
        if 'new' in args:
            cmp_data.diffType = ttypes.DiffType.NEW
        elif 'unresolved' in args:
            cmp_data.diffType = ttypes.DiffType.UNRESOLVED
        elif 'resolved' in args:
            cmp_data.diffType = ttypes.DiffType.RESOLVED

        results = getDiffResults(client, base_ids, cmp_data)

    printReports(client, results, args.output_format)


def handle_list_result_types(args):
    def getStatistics(client, run_ids, field, values):
        report_filter = ttypes.ReportFilter()
        setattr(report_filter, field, values)
        checkers = client.getCheckerCounts(run_ids,
                                           report_filter,
                                           None)

        return dict((res.name, res.count) for res in checkers)

    def checkerCount(dict, key):
        return dict[key] if key in dict else 0

    client = setup_client(args.product_url)

    if 'all_results' in args:
        items = check_run_names(client, None)
    else:
        items = check_run_names(client, args.names)

    run_ids = map(lambda run: run.runId, items.values())

    all_checkers_report_filter = ttypes.ReportFilter()
    all_checkers = client.getCheckerCounts(run_ids, all_checkers_report_filter,
                                           None)
    all_checkers_dict = dict((res.name, res) for res in all_checkers)

    unrev_checkers = getStatistics(client, run_ids, 'reviewStatus',
                                   [ttypes.ReviewStatus.UNREVIEWED])

    confirmed_checkers = getStatistics(client, run_ids, 'reviewStatus',
                                       [ttypes.ReviewStatus.CONFIRMED])

    false_checkers = getStatistics(client, run_ids, 'reviewStatus',
                                   [ttypes.ReviewStatus.FALSE_POSITIVE])

    intentional_checkers = getStatistics(client, run_ids, 'reviewStatus',
                                         [ttypes.ReviewStatus.INTENTIONAL])

    resolved_checkers = getStatistics(client, run_ids, 'detectionStatus',
                                      [ttypes.DetectionStatus.RESOLVED])

    all_results = []
    for key, checker_data in sorted(all_checkers_dict.items(),
                                    key=lambda x: x[1].severity,
                                    reverse=True):
        all_results.append(dict(
            checker=key,
            severity=ttypes.Severity._VALUES_TO_NAMES[checker_data.severity],
            reports=checker_data.count,
            unreviewed=checkerCount(unrev_checkers, key),
            confirmed=checkerCount(confirmed_checkers, key),
            false_positive=checkerCount(false_checkers, key),
            intentional=checkerCount(intentional_checkers, key),
            resolved=checkerCount(resolved_checkers, key),
         ))

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(all_results))
    else:
        header = ['Checker', 'Severity', 'All reports', 'Resolved',
                  'Unreviewed', 'Confirmed', 'False positive', "Intentional"]

        rows = []
        for stat in all_results:
            rows.append((stat['checker'],
                         stat['severity'],
                         str(stat['reports']),
                         str(stat['resolved']),
                         str(stat['unreviewed']),
                         str(stat['confirmed']),
                         str(stat['false_positive']),
                         str(stat['intentional'])))

        print(twodim_to_str(args.output_format, header, rows))


def handle_remove_run_results(args):
    client = setup_client(args.product_url)

    def is_later(d1, d2):
        dateformat = '%Y-%m-%d %H:%M:%S.%f'

        if not isinstance(d1, datetime):
            d1 = datetime.strptime(d1, dateformat)
        if not isinstance(d2, datetime):
            d2 = datetime.strptime(d2, dateformat)

        return d1 > d2

    if 'name' in args:
        check_run_names(client, args.name)

        def condition(name, runid, date):
            return name in args.name
    elif 'all_after_run' in args:
        run_info = check_run_names(client, [args.all_after_run])
        run_date = run_info[args.all_after_run].runDate

        def condition(name, runid, date):
            return is_later(date, run_date)
    elif 'all_before_run' in args:
        run_info = check_run_names(client, [args.all_before_run])
        run_date = run_info[args.all_before_run].runDate

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

    client.removeRunResults([run.runId for run
                            in client.getRunData(None)
                            if condition(run.name, run.runId, run.runDate)])

    LOG.info("Done.")


def handle_suppress(args):
    def bug_hash_filter(bug_id, filepath):
        filepath = '%' + filepath
        return [
            ttypes.ReportFilter(bugHash=bug_id, filepath=filepath),
            ttypes.ReportFilter(bugHash=bug_id, filepath=filepath)]

    limit = constants.MAX_QUERY_SIZE

    client = setup_client(args.product_url)

    run_info = check_run_names(client, [args.name])
    run = run_info.get(args.name)

    if 'input' in args:
        with open(args.input) as supp_file:
            suppress_data = suppress_file_handler.get_suppress_data(supp_file)

        for bug_id, file_name, comment in suppress_data:
            reports = client.getRunResults([run.runId], limit, 0, None,
                                           bug_hash_filter(bug_id, file_name),
                                           None)

            for report in reports:
                status = ttypes.ReviewStatus.FALSE_POSITIVE
                client.changeReviewStatus(report.reportId, status, comment)


def handle_login(args):
    protocol, host, port = split_server_url(args.server_url)
    handle_auth(protocol, host, port, args.username,
                login='logout' not in args)
