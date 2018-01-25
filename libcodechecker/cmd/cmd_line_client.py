# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import base64
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import os
import re
import sys
import shutil

from plist_to_html import PlistToHtml

from codeCheckerDBAccess_v6 import constants, ttypes

from libcodechecker import generic_package_context
from libcodechecker import logger
from libcodechecker import suppress_handler
from libcodechecker import suppress_file_handler
from libcodechecker.analyze import plist_parser
from libcodechecker.libclient.client import handle_auth
from libcodechecker.libclient.client import setup_client
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.report import Report
from libcodechecker.util import split_server_url


# Needs to be set in the handler functions.
LOG = None


def init_logger(level, logger_name='system'):
    logger.setup_logger(level)
    global LOG
    LOG = logger.get_logger(logger_name)


class CmdLineOutputEncoder(json.JSONEncoder):
    def default(self, o):
        d = {}
        d.update(o.__dict__)
        return d


def check_run_names(client, check_names):
    """
    Check if the given names are valid runs on the server. If any of the names
    is not found then the script finishes. Otherwise a dictionary returns which
    maps run names to runs. The dictionary contains only the runs in
    check_names or all runs if check_names is empty or None.
    """
    run_filter = ttypes.RunFilter()
    run_filter.names = check_names
    run_filter.exactMatch = check_names is not None

    run_info = {run.name: run for run in client.getRunData(run_filter)}

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

    init_logger(args.verbose)

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

    init_logger(args.verbose)

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

    init_logger(args.verbose)

    context = generic_package_context.get_context()

    def get_diff_results(client, baseids, cmp_data):

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

    def get_report_dir_results(reportdir):
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

    def get_line_from_file(filename, lineno):
        with open(filename, 'r') as f:
            i = 1
            for line in f:
                if i == lineno:
                    return line
                i += 1
        return ""

    def get_diff_base_results(client, baseids, base_hashes, suppressed_hashes):
        base_results = []
        report_filter = ttypes.ReportFilter()
        add_filter_conditions(report_filter, args.filter)

        sort_mode = [(ttypes.SortMode(
            ttypes.SortType.FILENAME,
            ttypes.Order.ASC))]
        limit = constants.MAX_QUERY_SIZE
        offset = 0

        report_filter.reportHash = base_hashes + suppressed_hashes
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
        return base_results

    def get_diff_report_dir(client, baseids, report_dir, cmp_data):
        filtered_reports = []
        report_dir_results = get_report_dir_results(report_dir)
        new_hashes = {}
        suppressed_in_code = []

        for rep in report_dir_results:
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

        base_hashes = client.getDiffResultsHash(baseids,
                                                new_hashes.keys(),
                                                cmp_data.diffType)

        if cmp_data.diffType == ttypes.DiffType.NEW or \
           cmp_data.diffType == ttypes.DiffType.UNRESOLVED:
            # Shows reports from the report dir which are not present in the
            # baseline (NEW reports) or appear in both side (UNRESOLVED
            # reports) and not suppressed in the code.
            for result in report_dir_results:
                h = result.main['issue_hash_content_of_line_in_context']
                if h in base_hashes and h not in suppressed_in_code:
                    filtered_reports.append(result)
        elif cmp_data.diffType == ttypes.DiffType.RESOLVED:
            # Show bugs in the baseline (server) which are not present in the
            # report dir or suppressed.
            results = get_diff_base_results(client, baseids, base_hashes,
                                            suppressed_in_code)
            for result in results:
                filtered_reports.append(result)

        return filtered_reports

    def cached_report_file_lookup(file_cache, file_id):
        """
        Get source file data for the given file and caches it in a file cache
        if file data is not found in the cache. Finally, it returns the source
        file data from the cache.
        """
        if file_id not in file_cache:
            source = client.getSourceFileData(file_id, True,
                                              ttypes.Encoding.BASE64)
            file_content = base64.b64decode(source.fileContent)
            file_cache[file_id] = {'id': file_id,
                                   'path': source.filePath,
                                   'content': file_content}

        return file_cache[file_id]

    def get_report_data(client, reports, file_cache):
        """
        Returns necessary report files and report data events for the HTML
        plist parser.
        """
        file_sources = {}
        report_data = []

        for report in reports:
            file_sources[report.fileId] = cached_report_file_lookup(
                file_cache, report.fileId)

            details = client.getReportDetails(report.reportId)
            events = []
            for index, event in enumerate(details.pathEvents):
                file_sources[event.fileId] = cached_report_file_lookup(
                    file_cache, event.fileId)

                events.append({'line': event.startLine,
                               'col': event.startCol,
                               'file': event.fileId,
                               'msg': event.msg,
                               'step': index + 1})
            report_data.append(events)

        return {'files': file_sources,
                'reports': report_data}

    def reports_to_report_data(reports):
        """
        Converts reports from Report class from one plist file
        to report data events for the HTML plist parser.
        """
        file_sources = {}
        fname_to_fid = {}
        report_data = []
        findex = 0

        for report in reports:
            # Not all report in this list may refer to the same files
            # thus we need to create a single file list with
            # all files from all reports.
            for f in report.files:
                if f not in fname_to_fid:
                    try:
                        content = open(f, 'r').read()
                    except (OSError, IOError):
                        content = f + " NOT FOUND."
                    file_sources[findex] = {'id': findex,
                                            'path': f,
                                            'content': content}
                    fname_to_fid[f] = findex
                    findex += 1

            events = []
            pathElements = report.bug_path
            index = 1
            for element in pathElements:
                if element['kind'] == 'event':
                    fname = report.files[element['location']['file']]
                    new_fid = fname_to_fid[fname]
                    events.append({'line': element['location']['line'],
                                   'col':  element['location']['col'],
                                   'file': new_fid,
                                   'msg':  element['message'],
                                   'step': index})
                    index += 1
            report_data.append(events)

        return {'files': file_sources,
                'reports': report_data}

    def report_to_html(client, reports, output_dir):
        """
        Generate HTML output files for the given reports in the given output
        directory by using the Plist To HTML parser.
        """
        html_builder = PlistToHtml.HtmlBuilder(context.path_plist_to_html_dist)

        file_report_map = defaultdict(list)
        for report in reports:
            file_path = ""
            if isinstance(report, Report):
                file_path = report.main['location']['file_name']
            else:
                file_path = report.checkedFile
            file_report_map[file_path].append(report)

        file_cache = {}
        for file_path, file_reports in file_report_map.items():
            checked_file = file_path
            filename = os.path.basename(checked_file)
            h = int(hashlib.md5(file_path).hexdigest(), 16) % (10 ** 8)

            if isinstance(file_reports[0], Report):
                report_data = reports_to_report_data(file_reports)
            else:
                report_data = get_report_data(client, file_reports, file_cache)

            output_path = os.path.join(output_dir,
                                       filename + '_' + str(h) + '.html')
            html_builder.create(output_path, report_data)
            print('Html file was generated for file://{0}: file://{1}'.format(
                checked_file, output_path))

    def print_reports(client, reports, output_format):
        output_dir = args.export_dir if 'export_dir' in args else None
        if 'clean' in args and os.path.isdir(output_dir):
            print("Previous analysis results in '{0}' have been removed, "
                  "overwriting with current results.".format(output_dir))
            shutil.rmtree(output_dir)

        if output_format == 'json':
            output = []
            for report in reports:
                if isinstance(report, Report):
                    output.append(report.main)
                else:
                    output.append(report)
            print(CmdLineOutputEncoder().encode(output))
            return

        if output_format == 'html':
            output_dir = args.export_dir
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            print("Generating HTML output files to file://{0} directory:\n"
                  .format(output_dir))

            report_to_html(client, reports, output_dir)

            print('\nTo view the results in a browser run:\n'
                  '  $ firefox {0}'.format(args.export_dir))
            return

        header = ['File', 'Checker', 'Severity', 'Msg', 'Source']
        rows = []

        source_lines = defaultdict(set)
        for report in reports:
            if not isinstance(report, Report):
                source_lines[report.fileId].add(report.line)

        lines_in_files_requested = []
        for key in source_lines:
            lines_in_files_requested.append(
                ttypes.LinesInFilesRequested(fileId=key,
                                             lines=source_lines[key]))

        source_line_contents = client.getLinesInSourceFileContents(
            lines_in_files_requested, ttypes.Encoding.BASE64)

        for report in reports:
            if isinstance(report, Report):
                # report is coming from a plist file.
                bug_line = report.main['location']['line']
                bug_col = report.main['location']['col']
                sev = 'unknown'
                checked_file = report.main['location']['file_name']\
                    + ':' + str(bug_line) + ":" + str(bug_col)
                check_name = report.main['check_name']
                check_msg = report.main['description']
                source_line =\
                    get_line_from_file(report.main['location']['file_name'],
                                       bug_line)
            else:
                # report is of ReportData type coming from CodeChecker server.
                bug_line = report.line
                bug_col = report.column
                sev = ttypes.Severity._VALUES_TO_NAMES[report.severity]
                checked_file = report.checkedFile + ':' + str(bug_line) +\
                    ":" + str(bug_col)
                source_line = base64.b64decode(
                    source_line_contents[report.fileId][bug_line])
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

    cmp_data = ttypes.CompareData()
    if 'new' in args:
        cmp_data.diffType = ttypes.DiffType.NEW
    elif 'unresolved' in args:
        cmp_data.diffType = ttypes.DiffType.UNRESOLVED
    elif 'resolved' in args:
        cmp_data.diffType = ttypes.DiffType.RESOLVED

    results = []
    if report_dir_mode:
        results = get_diff_report_dir(client, base_ids,
                                      os.path.abspath(args.newname),
                                      cmp_data)
    else:
        cmp_data.runIds = [newid]
        results = get_diff_results(client, base_ids, cmp_data)

    if len(results) == 0:
        LOG.info("No results.")
    else:
        print_reports(client, results, args.output_format)


def handle_list_result_types(args):

    init_logger(args.verbose)

    def get_statistics(client, run_ids, field, values):
        report_filter = ttypes.ReportFilter()
        report_filter.isUnique = True
        setattr(report_filter, field, values)
        checkers = client.getCheckerCounts(run_ids,
                                           report_filter,
                                           None,
                                           None,
                                           0)

        return dict((res.name, res.count) for res in checkers)

    def checker_count(checker_dict, key):
        return checker_dict.get(key, 0)

    client = setup_client(args.product_url)

    run_ids = None
    if 'all_results' not in args:
        items = check_run_names(client, args.names)
        run_ids = map(lambda run: run.runId, items.values())

    all_checkers_report_filter = ttypes.ReportFilter()
    all_checkers_report_filter.isUnique = True

    all_checkers = client.getCheckerCounts(run_ids,
                                           all_checkers_report_filter,
                                           None,
                                           None,
                                           0)
    all_checkers_dict = dict((res.name, res) for res in all_checkers)

    unrev_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                    [ttypes.ReviewStatus.UNREVIEWED])

    confirmed_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                        [ttypes.ReviewStatus.CONFIRMED])

    false_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                    [ttypes.ReviewStatus.FALSE_POSITIVE])

    intentional_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                          [ttypes.ReviewStatus.INTENTIONAL])

    resolved_checkers = get_statistics(client, run_ids, 'detectionStatus',
                                       [ttypes.DetectionStatus.RESOLVED])

    # Get severity counts
    report_filter = ttypes.ReportFilter()
    report_filter.isUnique = True
    sev_count = client.getSeverityCounts(run_ids, report_filter, None)
    severities = []
    for key, count in sorted(sev_count.items(),
                             reverse=True):
        severities.append(dict(
            severity=ttypes.Severity._VALUES_TO_NAMES[key],
            reports=count))

    all_results = []
    for key, checker_data in sorted(all_checkers_dict.items(),
                                    key=lambda x: x[1].severity,
                                    reverse=True):
        all_results.append(dict(
            checker=key,
            severity=ttypes.Severity._VALUES_TO_NAMES[checker_data.severity],
            reports=checker_data.count,
            unreviewed=checker_count(unrev_checkers, key),
            confirmed=checker_count(confirmed_checkers, key),
            false_positive=checker_count(false_checkers, key),
            intentional=checker_count(intentional_checkers, key),
            resolved=checker_count(resolved_checkers, key),
         ))

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(all_results))
        print(CmdLineOutputEncoder().encode(severities))
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

        # Print severity counts
        header = ['Severity', 'All reports']

        rows = []
        for stat in severities:
            rows.append((stat['severity'],
                         str(stat['reports'])))

        print(twodim_to_str(args.output_format, header, rows))


def handle_remove_run_results(args):

    init_logger(args.verbose)

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

    init_logger(args.verbose)

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

    init_logger(args.verbose)

    protocol, host, port = split_server_url(args.server_url)
    handle_auth(protocol, host, port, args.username,
                login='logout' not in args)
