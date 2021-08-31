# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Command line client.
"""


from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
import hashlib
import json
import os
from operator import itemgetter
import re
import sys
import shutil
import time
from typing import Dict, Iterable, List, Tuple, Union

from plist_to_html import PlistToHtml

from codechecker_api.codeCheckerDBAccess_v6 import constants, ttypes
from codechecker_api_shared.ttypes import RequestFailed

from codechecker_common import logger, plist_parser, util
from codechecker_common.checker_labels import CheckerLabels
from codechecker_common.report import Report
from codechecker_common.output import twodim, gerrit, codeclimate, baseline
from codechecker_report_hash.hash import get_report_path_hash

from codechecker_web.shared import webserver_context
from codechecker_web.shared import convert

from codechecker_client import report_type_converter
from .client import login_user, setup_client
from .cmd_line import CmdLineOutputEncoder
from .product import split_server_url

from . import suppress_file_handler

# Needs to be set in the handler functions.
LOG = None


BugPathLengthRange = namedtuple('BugPathLengthRange', ['min', 'max'])


def init_logger(level, stream=None, logger_name='system'):
    logger.setup_logger(level, stream)
    global LOG
    LOG = logger.get_logger(logger_name)


def filter_local_file_remote_run(
    run_args: List[str]
) -> Tuple[List[str], List[str], List[str]]:
    """
    Filter out arguments which are local directory, baseline files or remote
    run names.
    """
    local_dirs = []
    baseline_files = []
    run_names = []

    for r in run_args:
        if os.path.isdir(r):
            local_dirs.append(os.path.abspath(r))
        elif os.path.isfile(r) and baseline.check(r):
            baseline_files.append(os.path.abspath(r))
        else:
            run_names.append(r)

    return local_dirs, baseline_files, run_names


def run_sort_type_str(value):
    """ Converts the given run sort type to string. """
    if value == ttypes.RunSortType.NAME:
        return 'name'
    elif value == ttypes.RunSortType.UNRESOLVED_REPORTS:
        return 'unresolved_reports'
    elif value == ttypes.RunSortType.DATE:
        return 'date'
    elif value == ttypes.RunSortType.DURATION:
        return 'duration'
    elif value == ttypes.RunSortType.CC_VERSION:
        return 'codechecker_version'


def run_sort_type_enum(value):
    """ Returns the given run sort type Thrift enum value. """
    if value == 'name':
        return ttypes.RunSortType.NAME
    elif value == 'unresolved_reports':
        return ttypes.RunSortType.UNRESOLVED_REPORTS
    elif value == 'date':
        return ttypes.RunSortType.DATE
    elif value == 'duration':
        return ttypes.RunSortType.DURATION
    elif value == 'codechecker_version':
        return ttypes.RunSortType.CC_VERSION


def get_diff_type(args) -> Union[ttypes.DiffType, None]:
    """
    Returns Thrift DiffType value by processing the arguments.
    """
    if 'new' in args:
        return ttypes.DiffType.NEW

    if 'unresolved' in args:
        return ttypes.DiffType.UNRESOLVED

    if 'resolved' in args:
        return ttypes.DiffType.RESOLVED

    return None


def reports_to_html_report_data(reports: List[Report]) -> Dict:
    """
    Converts reports from Report class from one plist file
    to report data events for the HTML plist parser.
    """
    file_sources = {}
    report_data = []

    for report in reports:
        # Not all report in this list may refer to the same files
        # thus we need to create a single file list with
        # all files from all reports.
        for file_index, file_path in report.files.items():
            if file_index not in file_sources:
                try:
                    with open(file_path, 'r', encoding='utf-8',
                              errors='ignore') as source_data:
                        content = source_data.read()
                except (OSError, IOError):
                    content = file_path + " NOT FOUND."
                file_sources[file_index] = {'id': file_index,
                                            'path': file_path,
                                            'content': content}

        events = []
        for element in report.bug_path:
            kind = element['kind']
            if kind == 'event':
                events.append({'location': element['location'],
                               'message':  element['message']})

        macros = []
        for macro in report.macro_expansions:
            macros.append({'location': macro['location'],
                           'expansion': macro['expansion'],
                           'name': macro['name']})

        notes = []
        for note in report.notes:
            notes.append({'location': note['location'],
                          'message': note['message']})

        report_hash = report.main['issue_hash_content_of_line_in_context']
        report_data.append({
            'events': events,
            'macros': macros,
            'notes': notes,
            'path': report.file_path,
            'reportHash': report_hash,
            'checkerName': report.main['check_name']})

    return {'files': file_sources,
            'reports': report_data}


def get_run_tag(client, run_ids, tag_name):
    """Return run tag information for the given tag name in the given runs."""
    run_history_filter = ttypes.RunHistoryFilter()
    run_history_filter.tagNames = [tag_name]
    run_histories = client.getRunHistory(run_ids, None, None,
                                         run_history_filter)

    return run_histories[0] if run_histories else None


def process_run_args(client, run_args_with_tag):
    """Process the argument and returns run ids and run tag ids.

    The elemnts inside the given run_args_with_tag list has the following
    format: <run_name>:<run_tag>
    """
    run_ids = []
    run_names = []
    run_tags = []

    for run_arg_with_tag in run_args_with_tag:
        run_with_tag = run_arg_with_tag.split(':')
        run_name = run_with_tag[0]
        run_filter = ttypes.RunFilter(names=[run_name])

        runs = get_run_data(client, run_filter)
        if not runs:
            LOG.warning("No run names match the given pattern: %s",
                        run_arg_with_tag)
            sys.exit(1)

        r_ids = [run.runId for run in runs]
        run_ids.extend(r_ids)

        r_names = [run.name for run in runs]
        run_names.extend(r_names)

        # Set base run tag if it is available.
        run_tag_name = run_with_tag[1] if len(run_with_tag) > 1 else None
        if run_tag_name:
            tag = get_run_tag(client, r_ids, run_tag_name)
            if tag:
                run_tags.append(tag.id)

    return run_ids, run_names, run_tags


def get_suppressed_reports(reports: List[Report],
                           args: List[str]) -> List[str]:
    """Returns a list of suppressed report hashes."""
    return [rep.report_hash for rep in reports
            if not rep.check_source_code_comments(args.review_status)]


def get_report_dir_results(report_dirs: List[str],
                           args: List[str],
                           checker_labels: CheckerLabels) -> List[Report]:
    """Get reports from the given report directories.

    Absolute paths are expected to the given report directories.
    """
    all_reports = []
    processed_path_hashes = set()
    for report_dir in report_dirs:
        for filename in os.listdir(report_dir):
            if not filename.endswith(".plist"):
                continue

            file_path = os.path.join(report_dir, filename)
            LOG.debug("Parsing: %s", file_path)
            _, reports = plist_parser.parse_plist_file(file_path)
            LOG.debug("Parsing: %s done %s", file_path, len(reports))
            for report in reports:
                LOG.debug("get report hash")
                path_hash = get_report_path_hash(report)
                if path_hash in processed_path_hashes:
                    LOG.debug("Not showing report because it is a "
                              "deduplication of an already processed "
                              "report!")
                    LOG.debug("Path hash: %s", path_hash)
                    LOG.debug(report)
                    continue

                if skip_report_dir_result(report, args, checker_labels):
                    continue

                processed_path_hashes.add(path_hash)
                all_reports.append(report)

    return all_reports


def print_stats(report_count, file_stats, severity_stats):
    """Print summary of the report statistics."""
    print("\n----==== Summary ====----")
    if file_stats:
        vals = [[os.path.basename(k), v] for k, v in
                list(dict(file_stats).items())]
        vals.sort(key=itemgetter(0))
        keys = ['Filename', 'Report count']
        table = twodim.to_str('table', keys, vals, 1, True)
        print(table)

    if severity_stats:
        vals = [[k, v] for k, v in list(dict(severity_stats).items())]
        vals.sort(key=itemgetter(0))
        keys = ['Severity', 'Report count']
        table = twodim.to_str('table', keys, vals, 1, True)
        print(table)

    print("----=================----")
    print("Total number of reports: {}".format(report_count))
    print("----=================----\n")


def skip_report_dir_result(report, args, checker_labels):
    """Returns True if the report should be skipped from the results.

    Skipping is done based on the given filter set.
    """
    f_severities, f_checkers, f_file_path, _, _, _ = check_filter_values(args)

    if f_severities:
        severity_name = checker_labels.severity(report.main['check_name'])
        if severity_name.lower() not in list(map(str.lower, f_severities)):
            return True

    if f_checkers:
        checker_name = report.main['check_name']
        if not any([re.match(r'^' + c.replace("*", ".*") + '$',
                             checker_name, re.IGNORECASE)
                    for c in f_checkers]):
            return True

    if f_file_path:
        if not any([re.match(r'^' + f.replace("*", ".*") + '$',
                             report.file_path, re.IGNORECASE)
                    for f in f_file_path]):
            return True

    if 'checker_msg' in args:
        checker_msg = report.main['description']
        if not any([re.match(r'^' + c.replace("*", ".*") + '$',
                             checker_msg, re.IGNORECASE)
                    for c in args.checker_msg]):
            return True

    return False


def get_diff_base_results(client, args, baseids, base_hashes,
                          suppressed_hashes):
    """Get the run results from the server."""
    report_filter = ttypes.ReportFilter()
    add_filter_conditions(client, report_filter, args)
    report_filter.reportHash = base_hashes + suppressed_hashes

    sort_mode = [(ttypes.SortMode(
        ttypes.SortType.FILENAME,
        ttypes.Order.ASC))]

    limit = constants.MAX_QUERY_SIZE
    offset = 0

    base_results = []
    while True:
        results = client.getRunResults(baseids,
                                       limit,
                                       offset,
                                       sort_mode,
                                       report_filter,
                                       None,
                                       False)

        base_results.extend(results)
        offset += limit

        if len(results) < limit:
            break

    return base_results


def str_to_timestamp(date_str):
    """Return timestamp parsed from the given string parameter."""
    dateformat = '%Y-%m-%d %H:%M:%S.%f'
    date_time = date_str if isinstance(date_str, datetime) else \
        datetime.strptime(date_str, dateformat)

    return time.mktime(date_time.timetuple())


def check_run_names(client, check_names):
    """Check if the given names are valid runs on the server.

    If any of the names is not found then the script finishes.
    Otherwise a dictionary returns which maps run names to runs.
    The dictionary contains only the runs in check_names or
    all runs if check_names is empty or None.
    """
    run_filter = ttypes.RunFilter()
    run_filter.names = check_names
    run_filter.exactMatch = check_names is not None

    run_info = {run.name: run for run in get_run_data(client, run_filter)}

    if not check_names:
        return run_info

    missing_names = [name for name in check_names if not run_info.get(name)]
    if missing_names:
        LOG.warning("The following runs were not found in the database: %s.",
                    ', '.join(missing_names))
        sys.exit(1)

    return run_info


def check_deprecated_arg_usage(args):
    if 'suppressed' in args:
        LOG.warning('"--suppressed" option has been deprecated. Use '
                    '"--review-status" option to get false positive '
                    '(suppressed) results.')

    if 'filter' in args:
        LOG.warning('"--filter" option has been deprecated. Use '
                    'separate filter options of this command to filter the '
                    'results. For more information see the help.')

    if 'detected_at' in args:
        LOG.warning('"--detected-at" option has been deprecated. Use '
                    '--detected-before/--detected-after options to filter the '
                    'results by detection date. For more information see the '
                    'help.')

    if 'fixed_at' in args:
        LOG.warning('"--fixed-at" option has been deprecated. Use '
                    '--fixed-before/--fixed-after options to filter the '
                    'results by fix date. For more information see the '
                    'help.')


def get_run_data(client, run_filter, sort_mode=None,
                 limit=constants.MAX_QUERY_SIZE):
    """Get all runs based on the given run filter."""

    all_runs = []

    offset = 0
    while True:
        runs = runs = client.getRunData(run_filter, limit, offset, sort_mode)
        all_runs.extend(runs)
        offset += limit

        if len(runs) < limit:
            break

    return all_runs


def get_run_results(client,
                    run_ids,
                    limit,
                    offset,
                    sort_type,
                    report_filter,
                    compare_data,
                    query_report_details):
    """Get all the results with multiple api request.

    In each api request get the limit ammount of reports.
    Collect and return all the reports based on the filters.
    """

    all_results = []
    while True:
        results = client.getRunResults(run_ids,
                                       limit,
                                       offset,
                                       sort_type,
                                       report_filter,
                                       compare_data,
                                       query_report_details)
        all_results.extend(results)
        offset += limit
        if len(results) < limit:
            break

    return all_results


def validate_filter_values(user_values, valid_values, value_type):
    """
    Check if the value provided by the user is a valid value.
    """
    if not user_values:
        return True

    non_valid_values = [status for status in user_values
                        if valid_values.get(status.upper(), None) is None]

    if non_valid_values:
        invalid_values = ','.join([x.lower() for x in non_valid_values])
        LOG.error('Invalid %s value(s): %s', value_type, invalid_values)

        valid_values = ','.join([x.lower() for x in valid_values.keys()])
        LOG.error('Valid values are: %s', valid_values)

        return False

    return True


def check_filter_values(args):
    """
    Check if filter values are valid values. Returns values which are checked
    or exit from the interpreter.
    """
    severities = checkers = file_path = dt_statuses = rw_statuses = None
    bug_path_length = None

    filter_str = args.filter if 'filter' in args else None
    if filter_str:
        if filter_str.count(':') != 4:
            LOG.warning("Filter string has to contain four colons (e.g. "
                        "\"high,medium:unix,core:*.cpp:new,unresolved:"
                        "false_positive,intentional\").")
        else:
            filter_values = []
            for x in filter_str.strip().split(':'):
                values = [y.strip() for y in x.strip().split(',') if y.strip()]
                filter_values.append(values if values else None)

            # pylint: disable=unbalanced-tuple-unpacking
            severities, checkers, file_path, dt_statuses, rw_statuses = \
                filter_values

    if 'severity' in args:
        severities = args.severity

    if 'detection_status' in args:
        dt_statuses = args.detection_status

    if 'review_status' in args:
        rw_statuses = args.review_status

    if 'checker_name' in args:
        checkers = args.checker_name

    if 'file_path' in args:
        file_path = args.file_path

    if 'bug_path_length' in args:
        path_lengths = args.bug_path_length.split(':')

        min_bug_path_length = int(path_lengths[0]) if \
            path_lengths and path_lengths[0].isdigit() else None

        max_bug_path_length = int(path_lengths[1]) if \
            len(path_lengths) > 1 and path_lengths[1].isdigit() else None

        bug_path_length = BugPathLengthRange(min=min_bug_path_length,
                                             max=max_bug_path_length)

    values_to_check = [
        (severities, ttypes.Severity._NAMES_TO_VALUES, 'severity'),
        (dt_statuses, ttypes.DetectionStatus._NAMES_TO_VALUES,
         'detection status'),
        (rw_statuses, ttypes.ReviewStatus._NAMES_TO_VALUES,
         'review status')]

    if not all(valid for valid in
               [validate_filter_values(*x) for x in values_to_check]):
        sys.exit(1)
    return severities, checkers, file_path, dt_statuses, rw_statuses, \
        bug_path_length


def add_filter_conditions(client, report_filter, args):
    """
    This function fills some attributes of the given report filter based on
    the arguments which is provided in the command line.
    """

    severities, checkers, file_path, dt_statuses, rw_statuses, \
        bug_path_length = check_filter_values(args)

    report_filter.isUnique = args.uniqueing == 'on'

    if severities:
        report_filter.severity = [
            ttypes.Severity._NAMES_TO_VALUES[x.upper()] for x in severities]

    if dt_statuses:
        report_filter.detectionStatus = [
            ttypes.DetectionStatus._NAMES_TO_VALUES[x.upper()] for x in
            dt_statuses]

    if rw_statuses:
        report_filter.reviewStatus = [
            ttypes.ReviewStatus._NAMES_TO_VALUES[x.upper()] for x in
            rw_statuses]

    if checkers:
        report_filter.checkerName = checkers

    if 'checker_msg' in args:
        report_filter.checkerMsg = args.checker_msg

    if 'analyzer_name' in args:
        report_filter.analyzerNames = args.analyzer_name

    if 'component' in args:
        report_filter.componentNames = args.component

    if 'report_hash' in args:
        report_filter.reportHash = args.report_hash

    if file_path:
        report_filter.filepath = file_path

    if bug_path_length:
        report_filter.bugPathLength = \
            ttypes.BugPathLengthRange(min=bug_path_length.min,
                                      max=bug_path_length.max)

    if 'tag' in args:
        run_history_filter = ttypes.RunHistoryFilter(tagNames=args.tag)
        run_histories = client.getRunHistory(None, None, None,
                                             run_history_filter)
        if run_histories:
            report_filter.runTag = [t.id for t in run_histories]

    if 'open_reports_date' in args:
        report_filter.openReportsDate = \
            int(str_to_timestamp(args.open_reports_date))

    if 'detected_at' in args:
        report_filter.firstDetectionDate = \
            int(str_to_timestamp(args.detected_at))

    if 'fixed_at' in args:
        report_filter.fixDate = int(str_to_timestamp(args.fixed_at))

    detected_at = None
    fixed_at = None

    if 'detected_before' in args or 'detected_after' in args:
        detected_at = ttypes.DateInterval()

        if 'detected_before' in args:
            detected_at.before = int(str_to_timestamp(args.detected_before))

        if 'detected_after' in args:
            detected_at.after = int(str_to_timestamp(args.detected_after))

    if 'fixed_before' in args or 'fixed_after' in args:
        fixed_at = ttypes.DateInterval()

        if 'fixed_before' in args:
            fixed_at.before = int(str_to_timestamp(args.fixed_before))

        if 'fixed_after' in args:
            fixed_at.after = int(str_to_timestamp(args.fixed_after))

    if detected_at or fixed_at:
        report_filter.date = ttypes.ReportDate(detected=detected_at,
                                               fixed=fixed_at)


def process_run_filter_conditions(args):
    """
    This function fills some attributes of the given run filter based on
    the arguments which is provided in the command line.
    """
    run_filter = ttypes.RunFilter()

    if 'names' in args:
        run_filter.names = args.names
        run_filter.exactMatch = False
    elif 'all_after_run' in args:
        run_filter.afterRun = args.all_after_run
    elif 'all_before_run' in args:
        run_filter.beforeRun = args.all_before_run
    elif 'all_after_time' in args:
        run_filter.afterTime = int(str_to_timestamp(args.all_after_time))
    elif 'all_before_time' in args:
        run_filter.beforeTime = int(str_to_timestamp(args.all_before_time))

    return run_filter


# ---------------------------------------------------------------------------
# Argument handlers for the 'CodeChecker cmd' subcommands.
# ---------------------------------------------------------------------------


def handle_list_runs(args):
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    client = setup_client(args.product_url)

    run_filter = process_run_filter_conditions(args)

    sort_type = run_sort_type_enum(args.sort_type)
    sort_order = ttypes.Order._NAMES_TO_VALUES[args.sort_order.upper()]
    sort_mode = ttypes.RunSortMode(sort_type, sort_order)

    runs = get_run_data(client, run_filter, sort_mode)

    if args.output_format == 'json':
        # This json is different from the json format printed by the
        # parse command. This json converts the ReportData type report
        # to a json format.
        results = []
        for run in runs:
            results.append({run.name: run})
        print(CmdLineOutputEncoder().encode(results))

    else:  # plaintext, csv
        header = ['Name', 'Number of unresolved reports',
                  'Analyzer statistics', 'Storage date', 'Version tag',
                  'Duration', 'Description', 'CodeChecker version']
        rows = []
        for run in runs:
            duration = str(timedelta(seconds=run.duration)) \
                if run.duration > -1 else 'Not finished'

            analyzer_statistics = []
            for analyzer in run.analyzerStatistics:
                stat = run.analyzerStatistics[analyzer]
                num_of_all_files = stat.successful + stat.failed
                analyzer_statistics.append(analyzer + ' (' +
                                           str(num_of_all_files) + '/' +
                                           str(stat.successful) + ')')

            codechecker_version = run.codeCheckerVersion \
                if run.codeCheckerVersion else ''
            description = run.description if run.description else ''

            rows.append((run.name,
                         str(run.resultCount),
                         ', '.join(analyzer_statistics),
                         run.runDate,
                         run.versionTag if run.versionTag else '',
                         duration,
                         description,
                         codechecker_version))

        print(twodim.to_str(args.output_format, header, rows))


def handle_list_results(args):
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    check_deprecated_arg_usage(args)

    client = setup_client(args.product_url)

    run_filter = ttypes.RunFilter(names=args.names)

    run_ids = [run.runId for run in get_run_data(client, run_filter)]
    if not run_ids:
        LOG.warning("No runs were found!")
        sys.exit(1)

    report_filter = ttypes.ReportFilter()
    add_filter_conditions(client, report_filter, args)

    query_report_details = args.details and args.output_format == 'json' \
        if 'details' in args else None

    all_results = get_run_results(client,
                                  run_ids,
                                  constants.MAX_QUERY_SIZE,
                                  0,
                                  None,
                                  report_filter,
                                  None,
                                  query_report_details)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(all_results))
    else:
        header = ['File', 'Checker', 'Severity', 'Message', 'Bug path length',
                  'Analyzer name', 'Review status', 'Detection status']

        rows = []
        max_msg_len = 50
        for res in all_results:
            bug_line = res.line
            checked_file = res.checkedFile
            if bug_line is not None:
                checked_file += ' @ ' + str(bug_line)

            sev = ttypes.Severity._VALUES_TO_NAMES[res.severity]
            rw_status = \
                ttypes.ReviewStatus._VALUES_TO_NAMES[res.reviewData.status]

            dt_status = 'N/A'

            status = res.detectionStatus
            if status is not None:
                dt_status = ttypes.DetectionStatus._VALUES_TO_NAMES[status]

            # Remove whitespace characters from the checker message.
            msg = re.sub(r'\s+', ' ', res.checkerMsg)

            # Avoid too long cell content.
            if len(msg) > max_msg_len:
                msg = msg[:max_msg_len] + '...'

            rows.append((checked_file, res.checkerId, sev, msg,
                         res.bugPathLength, res.analyzerName, rw_status,
                         dt_status))

        print(twodim.to_str(args.output_format, header, rows))


def handle_diff_results(args):
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    if len(args.output_format) > 1 and ('export_dir' not in args):
        LOG.error("Export directory is required if multiple output formats "
                  "are selected!")
        sys.exit(1)

    if 'gerrit' in args.output_format and \
            not gerrit.mandatory_env_var_is_set():
        sys.exit(1)

    check_deprecated_arg_usage(args)
    context = webserver_context.get_context()
    source_line_contents = {}

    def get_diff_local_dir_remote_run(
        client,
        report_dirs: List[str],
        baseline_files: List[str],
        remote_run_names: List[str]
    ):
        """ Compare a local report directory with a remote run. """
        filtered_reports = []

        filtered_report_hashes = set()

        report_dir_results = get_report_dir_results(
            report_dirs, args, context.checker_labels)
        suppressed_in_code = get_suppressed_reports(report_dir_results, args)

        diff_type = get_diff_type(args)
        run_ids, run_names, tag_ids = \
            process_run_args(client, remote_run_names)
        local_report_hashes = set([r.report_hash for r in report_dir_results])
        local_report_hashes.update(baseline.get_report_hashes(baseline_files))

        if diff_type == ttypes.DiffType.NEW:
            # Get report hashes which can be found only in the remote runs.
            remote_hashes = client.getDiffResultsHash(
                run_ids, local_report_hashes, ttypes.DiffType.RESOLVED,
                None, tag_ids)

            results = get_diff_base_results(
                client, args, run_ids, remote_hashes, suppressed_in_code)

            for result in results:
                filtered_reports.append(result)
        elif diff_type == ttypes.DiffType.UNRESOLVED:
            # Get remote hashes which can be found in the remote run and in the
            # local report directory.
            remote_hashes = client.getDiffResultsHash(
                run_ids, local_report_hashes, ttypes.DiffType.UNRESOLVED,
                None, tag_ids)

            filtered_report_hashes = local_report_hashes.copy()
            for result in report_dir_results:
                rep_h = result.report_hash
                filtered_report_hashes.discard(rep_h)
                if rep_h in remote_hashes and rep_h not in suppressed_in_code:
                    filtered_reports.append(result)
            filtered_report_hashes &= set(remote_hashes)

            # Try to get missing report from the server based on the report
            # hashes.
            if filtered_report_hashes:
                results = get_diff_base_results(
                    client, args, run_ids, list(filtered_report_hashes),
                    suppressed_in_code)

                for result in results:
                    filtered_report_hashes.discard(result.bugHash)
                    filtered_reports.append(result)
        elif diff_type == ttypes.DiffType.RESOLVED:
            # Get remote hashes which can be found in the remote run and in the
            # local report directory.
            remote_hashes = client.getDiffResultsHash(
                run_ids, local_report_hashes, ttypes.DiffType.UNRESOLVED,
                None, tag_ids)

            filtered_report_hashes = local_report_hashes.copy()
            for result in report_dir_results:
                filtered_report_hashes.discard(result.report_hash)
                if result.report_hash not in remote_hashes:
                    filtered_reports.append(result)
            filtered_report_hashes -= set(remote_hashes)

        return filtered_reports, filtered_report_hashes, run_names

    def get_diff_remote_run_local_dir(
        client,
        remote_run_names: List[str],
        report_dirs: List[str],
        baseline_files: List[str]
    ):
        """ Compares a remote run with a local report directory. """
        filtered_reports = []
        filtered_report_hashes = []

        report_dir_results = get_report_dir_results(
            report_dirs, args, context.checker_labels)
        suppressed_in_code = get_suppressed_reports(report_dir_results, args)

        diff_type = get_diff_type(args)
        run_ids, run_names, tag_ids = \
            process_run_args(client, remote_run_names)
        local_report_hashes = set([r.report_hash for r in report_dir_results])

        local_report_hashes = local_report_hashes.union(
            baseline.get_report_hashes(baseline_files))

        remote_hashes = client.getDiffResultsHash(
            run_ids, local_report_hashes, diff_type, None, tag_ids)

        if not remote_hashes:
            return filtered_reports, filtered_report_hashes, run_names

        if diff_type in [ttypes.DiffType.NEW, ttypes.DiffType.UNRESOLVED]:
            # Shows reports from the report dir which are not present in
            # the baseline (NEW reports) or appear in both side (UNRESOLVED
            # reports) and not suppressed in the code.
            filtered_report_hashes = set(remote_hashes)

            for result in report_dir_results:
                rep_h = result.report_hash
                filtered_report_hashes.discard(rep_h)
                if rep_h in remote_hashes and rep_h not in suppressed_in_code:
                    filtered_reports.append(result)
        elif diff_type == ttypes.DiffType.RESOLVED:
            # Show bugs in the baseline (server) which are not present in
            # the report dir or suppressed.
            results = get_diff_base_results(
                client, args, run_ids, remote_hashes, suppressed_in_code)

            for result in results:
                filtered_reports.append(result)

        return filtered_reports, filtered_report_hashes, run_names

    def get_diff_remote_runs(client, remote_base_run_names,
                             remote_new_run_names):
        """
        Compares two remote runs and returns the filtered results.
        """
        report_filter = ttypes.ReportFilter()
        add_filter_conditions(client, report_filter, args)

        base_ids, base_run_names, base_run_tags = \
            process_run_args(client, remote_base_run_names)
        report_filter.runTag = base_run_tags

        cmp_data = ttypes.CompareData()
        cmp_data.diffType = get_diff_type(args)

        new_ids, new_run_names, new_run_tags = \
            process_run_args(client, remote_new_run_names)
        cmp_data.runIds = new_ids
        cmp_data.runTag = new_run_tags

        # Do not show resolved bugs in compare mode new.
        if cmp_data.diffType == ttypes.DiffType.NEW:
            report_filter.detectionStatus = [
                ttypes.DetectionStatus.NEW,
                ttypes.DetectionStatus.UNRESOLVED,
                ttypes.DetectionStatus.REOPENED]

        sort_mode = [(ttypes.SortMode(
            ttypes.SortType.FILENAME,
            ttypes.Order.ASC))]

        all_results = get_run_results(client,
                                      base_ids,
                                      constants.MAX_QUERY_SIZE,
                                      0,
                                      sort_mode,
                                      report_filter,
                                      cmp_data,
                                      False)

        return all_results, base_run_names, new_run_names

    def get_diff_local_dirs(
        report_dirs: List[str],
        baseline_files: List[str],
        new_report_dirs: List[str],
        new_baseline_files: List[str]
    ) -> Tuple[List[Report], List[str]]:
        """
        Compares two report directories and returns the filtered results.
        """
        filtered_reports = []
        filtered_report_hashes = []

        base_results = get_report_dir_results(
            report_dirs, args, context.checker_labels)
        new_results = get_report_dir_results(
            new_report_dirs, args, context.checker_labels)

        new_results = [res for res in new_results
                       if res.check_source_code_comments(args.review_status)]

        base_hashes = set([res.report_hash for res in base_results])
        new_hashes = set([res.report_hash for res in new_results])

        # Add hashes from the baseline files.
        base_hashes.update(baseline.get_report_hashes(baseline_files))
        new_hashes.update(baseline.get_report_hashes(new_baseline_files))

        diff_type = get_diff_type(args)
        if diff_type == ttypes.DiffType.NEW:
            filtered_report_hashes = new_hashes.copy()
            for res in new_results:
                filtered_report_hashes.discard(res.report_hash)

                if res.report_hash not in base_hashes:
                    filtered_reports.append(res)
        if diff_type == ttypes.DiffType.UNRESOLVED:
            filtered_report_hashes = new_hashes.copy()
            for res in new_results:
                filtered_report_hashes.discard(res.report_hash)

                if res.report_hash in base_hashes:
                    filtered_reports.append(res)
        elif diff_type == ttypes.DiffType.RESOLVED:
            filtered_report_hashes = base_hashes.copy()
            for res in base_results:
                filtered_report_hashes.discard(res.report_hash)

                if res.report_hash not in new_hashes:
                    filtered_reports.append(res)

        return filtered_reports, filtered_report_hashes

    def cached_report_file_lookup(file_cache, file_id):
        """
        Get source file data for the given file and caches it in a file cache
        if file data is not found in the cache. Finally, it returns the source
        file data from the cache.
        """
        if file_id not in file_cache:
            source = client.getSourceFileData(file_id, True,
                                              ttypes.Encoding.BASE64)
            file_content = convert.from_b64(source.fileContent)
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
            for event in details.pathEvents:
                file_sources[event.fileId] = cached_report_file_lookup(
                    file_cache, event.fileId)

                location = {'line': event.startLine,
                            'col': event.startCol,
                            'file': event.fileId}

                events.append({'location': location,
                               'message': event.msg})

            # Get extended data.
            macros = []
            notes = []
            for extended_data in details.extendedData:
                file_sources[extended_data.fileId] = cached_report_file_lookup(
                    file_cache, extended_data.fileId)

                location = {'line': extended_data.startLine,
                            'col': extended_data.startCol,
                            'file': extended_data.fileId}

                if extended_data.type == ttypes.ExtendedReportDataType.MACRO:
                    macros.append({'location': location,
                                   'expansion': event.msg})
                elif extended_data.type == ttypes.ExtendedReportDataType.NOTE:
                    notes.append({'location': location,
                                  'message': event.msg})

            report_data.append({
                'events': events,
                'macros': macros,
                'notes': notes,
                'path': report.checkedFile,
                'reportHash': report.bugHash,
                'checkerName': report.checkerId})

        return {'files': file_sources,
                'reports': report_data}

    def report_to_html(client, reports, output_dir):
        """
        Generate HTML output files for the given reports in the given output
        directory by using the Plist To HTML builder.
        """
        html_builder = PlistToHtml.HtmlBuilder(
            context.path_plist_to_html_dist,
            context.checker_labels)
        file_stats = defaultdict(int)
        severity_stats = defaultdict(int)
        file_report_map = defaultdict(list)
        for report in reports:
            if isinstance(report, Report):
                file_path = report.file_path

                check_name = report.main['check_name']
                sev = context.checker_labels.severity(check_name)
            else:
                file_path = report.checkedFile
                sev = ttypes.Severity._VALUES_TO_NAMES[report.severity]

            file_report_map[file_path].append(report)
            file_stats[file_path] += 1
            severity_stats[sev] += 1

        file_cache = {}
        for file_path, file_reports in file_report_map.items():
            checked_file = file_path
            filename = os.path.basename(checked_file)
            h = int(
                hashlib.md5(
                    file_path.encode('utf-8')).hexdigest(),
                16) % (10 ** 8)

            if isinstance(file_reports[0], Report):
                report_data = reports_to_html_report_data(file_reports)
            else:
                report_data = get_report_data(client, file_reports, file_cache)

            output_path = os.path.join(output_dir,
                                       filename + '_' + str(h) + '.html')
            html_builder.create(output_path, report_data)
            print('Html file was generated for file://{0}: file://{1}'.format(
                checked_file, output_path))

        html_builder.create_index_html(output_dir)
        print_stats(len(reports), file_stats, severity_stats)

    def print_reports(
        client,
        reports: List[Report],
        report_hashes: Iterable[str],
        output_formats: List[str]
    ):
        if report_hashes:
            LOG.info("Couldn't get local reports for the following baseline "
                     "report hashes: %s", ', '.join(sorted(report_hashes)))

        selected_output_format_num = len(output_formats)

        if 'json' in output_formats:
            out = []
            for report in reports:
                if isinstance(report, Report):
                    report = \
                        report_type_converter.report_to_reportData(
                            report, context.checker_labels)
                    out.append(report)
                else:
                    out.append(report)

            encoded_reports = CmdLineOutputEncoder().encode(out)
            if output_dir:
                report_json = os.path.join(output_dir, 'reports.json')

                with open(report_json, mode="w", encoding="utf-8",
                          errors="ignore") as reports_file:
                    reports_file.write(encoded_reports)
                LOG.info('JSON report file was created: %s',
                         os.path.join(output_dir, 'report.json'))

            else:
                print(encoded_reports)

            # Json was the only format specified.
            if selected_output_format_num == 1:
                return

            output_formats.remove('json')

        if 'html' in output_formats:
            print("Generating HTML output files to file://{0} directory:\n"
                  .format(output_dir))

            report_to_html(client, reports, output_dir)

            print('\nTo view the results in a browser run:\n'
                  '  $ firefox {0}\n'.format(os.path.join(output_dir,
                                                          'index.html')))

            # HTML was the only format specified.
            if selected_output_format_num == 1:
                return

            output_formats.remove('html')

        # Collect source line contents for the report type got from the server.
        source_lines = defaultdict(set)
        for report in reports:
            if not isinstance(report, Report) and report.line is not None:
                source_lines[report.fileId].add(report.line)
        if client:
            lines_in_files_requested = []
            for key in source_lines:
                lines_in_files_requested.append(
                    ttypes.LinesInFilesRequested(fileId=key,
                                                 lines=source_lines[key]))

            source_line_contents.update(client.getLinesInSourceFileContents(
                lines_in_files_requested, ttypes.Encoding.BASE64))

        # Convert all the reports to the common Report
        # type for printing and formatting to various formats.
        converted_reports = []
        changed_files = set()
        for report in reports:
            if not isinstance(report, Report):
                r = report_type_converter.reportData_to_report(report)
                if source_line_contents:
                    r.source_line = convert.from_b64(
                        source_line_contents[report.fileId][report.line])
                converted_reports.append(r)
            else:
                if not os.path.exists(report.file_path):
                    changed_files.add(report.file_path)
                    continue

                report.source_line = util.get_line(report.file_path,
                                                   report.line)

                converted_reports.append(report)

        reports = converted_reports

        repo_dir = os.environ.get('CC_REPO_DIR')
        if repo_dir:
            for report in reports:
                report.trim_path_prefixes([repo_dir])

        if 'gerrit' in output_formats:
            gerrit_reports = gerrit.convert(reports, context.checker_labels)

            # Gerrit was the only format specified.
            if selected_output_format_num == 1 and not output_dir:
                print(json.dumps(gerrit_reports))
                return

            gerrit_review_json = os.path.join(output_dir,
                                              'gerrit_review.json')
            with open(gerrit_review_json, 'w') as review_file:
                json.dump(gerrit_reports, review_file)
            LOG.info("Gerrit review file was created: %s\n",
                     gerrit_review_json)

            output_formats.remove('gerrit')

        if 'codeclimate' in output_formats:
            cc_reports = codeclimate.convert(reports, context.checker_labels)
            # Codelimate was the only format specified.
            if selected_output_format_num == 1 and not output_dir:
                print(json.dumps(cc_reports))
                return

            codeclimate_issues_json = os.path.join(output_dir,
                                                   'codeclimate_issues.json')
            with open(codeclimate_issues_json, 'w') as issues_f:
                json.dump(cc_reports, issues_f)

            LOG.info("Code Climate file was created: %s\n",
                     codeclimate_issues_json)

            output_formats.remove('codeclimate')

        header = ['File', 'Checker', 'Severity', 'Msg', 'Source']
        rows = []

        file_stats = defaultdict(int)
        severity_stats = defaultdict(int)

        for report in reports:
            if report.source_line is None:
                continue

            severity = context.checker_labels.severity(report.check_name)
            file_name = report.file_path
            checked_file = file_name \
                + ':' + str(report.line) + ":" + str(report.col)
            check_msg = report.description

            rows.append((severity,
                         checked_file,
                         check_msg,
                         report.check_name,
                         report.source_line))

            severity_stats[severity] += 1
            file_stats[file_name] += 1

        for output_format in output_formats:
            if output_format == 'plaintext':
                for row in rows:
                    print("[{0}] {1}: {2} [{3}]\n{4}\n".format(
                        row[0], row[1], row[2], row[3], row[4]))
            else:
                print(twodim.to_str(output_format, header, rows))

        print_stats(len(reports), file_stats, severity_stats)

        if changed_files:
            changed_f = '\n'.join([' - ' + f for f in changed_files])
            LOG.warning("The following source file contents changed since the "
                        "latest analysis:\n%s\nMultiple reports were not "
                        "shown and skipped from the statistics. Please "
                        "analyze your project again to update the "
                        "reports!", changed_f)

    basename_local_dirs, basename_baseline_files, basename_run_names = \
        filter_local_file_remote_run(args.base_run_names)

    newname_local_dirs, newname_baseline_files, newname_run_names = \
        filter_local_file_remote_run(args.new_run_names)

    has_different_run_args = False
    if (basename_local_dirs or basename_baseline_files) and basename_run_names:
        LOG.error("All base run names must have the same type: local "
                  "directory (%s) / baseline files (%s) or run names (%s).",
                  ', '.join(basename_local_dirs),
                  ', '.join(basename_baseline_files),
                  ', '.join(basename_run_names))
        has_different_run_args = True

    if newname_local_dirs and newname_run_names:
        LOG.error("All new run names must have the same type: local "
                  "directory (%s) / baseline files (%s) or run names (%s).",
                  ', '.join(newname_local_dirs),
                  ', '.join(newname_baseline_files),
                  ', '.join(newname_run_names))
        has_different_run_args = True

    if has_different_run_args:
        sys.exit(1)

    output_dir = args.export_dir if 'export_dir' in args else None
    if 'clean' in args and os.path.isdir(output_dir):
        print("Previous analysis results in '{0}' have been removed, "
              "overwriting with current results.".format(output_dir))
        shutil.rmtree(output_dir)

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if basename_local_dirs:
        LOG.info("Matching local report directories (--baseline): %s",
                 ', '.join(basename_local_dirs))
    if basename_baseline_files:
        LOG.info("Matching local baseline files (--baseline): %s",
                 ', '.join(basename_baseline_files))

    if newname_local_dirs:
        LOG.info("Matching local report directories (--newname): %s",
                 ', '.join(newname_local_dirs))
    if newname_baseline_files:
        LOG.info("Matching local baseline files (--newname): %s",
                 ', '.join(newname_baseline_files))

    client = None
    # We set up the client if we are not comparing two local report directories
    # or baseline files.
    if basename_run_names or newname_run_names:
        if basename_run_names:
            LOG.info("Given remote runs (--baseline): %s",
                     ', '.join(basename_run_names))
        if newname_run_names:
            LOG.info("Given remote runs (--newname): %s",
                     ', '.join(newname_run_names))

        try:
            client = setup_client(args.product_url)
        except SystemExit as sexit:
            LOG.error("Failed to get remote runs from server! Please "
                      "make sure that CodeChecker server is running on host "
                      "'%s' or these are valid directory paths!",
                      args.product_url)
            raise sexit

    report_hashes = []
    if (basename_local_dirs or basename_baseline_files) and \
       (newname_local_dirs or newname_baseline_files):
        reports, report_hashes = get_diff_local_dirs(
            basename_local_dirs, basename_baseline_files,
            newname_local_dirs, newname_baseline_files)

        print_reports(client, reports, report_hashes, args.output_format)
        LOG.info("Compared the following local files / directories: %s and %s",
                 ', '.join([*basename_local_dirs, *basename_baseline_files]),
                 ', '.join([*newname_local_dirs, *newname_baseline_files]))
    elif newname_local_dirs or newname_baseline_files:
        reports, report_hashes, matching_base_run_names = \
            get_diff_remote_run_local_dir(
                client, basename_run_names,
                newname_local_dirs, newname_baseline_files)

        print_reports(client, reports, report_hashes, args.output_format)
        LOG.info("Compared remote run(s) %s (matching: %s) and local files / "
                 "report directory(s) %s",
                 ', '.join(basename_run_names),
                 ', '.join(matching_base_run_names),
                 ', '.join([*newname_local_dirs, *newname_baseline_files]))
    elif (basename_local_dirs or basename_baseline_files):
        reports, report_hashes, matching_new_run_names = \
            get_diff_local_dir_remote_run(
                client, basename_local_dirs, basename_baseline_files,
                newname_run_names)

        print_reports(client, reports, report_hashes, args.output_format)
        LOG.info("Compared local files / report directory(s) %s and remote "
                 "run(s) %s (matching: %s).",
                 ', '.join([*basename_local_dirs, *basename_baseline_files]),
                 ', '.join(newname_run_names),
                 ', '.join(matching_new_run_names))
    else:
        reports, matching_base_run_names, matching_new_run_names = \
            get_diff_remote_runs(client, basename_run_names, newname_run_names)
        print_reports(client, reports, None, args.output_format)
        LOG.info("Compared multiple remote runs %s (matching: %s) and %s "
                 "(matching: %s)",
                 ', '.join(basename_run_names),
                 ', '.join(matching_base_run_names),
                 ', '.join(newname_run_names),
                 ', '.join(matching_new_run_names))

    if len(reports) != 0 or len(report_hashes) != 0:
        sys.exit(2)


def handle_list_result_types(args):
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)
    check_deprecated_arg_usage(args)

    if 'disable_unique' in args:
        LOG.warning("--disable-unique option is deprecated. Please use the "
                    "'--uniqueing on' option to get uniqueing results.")
        args.uniqueing = 'off'

    def get_statistics(client, run_ids, field, values):
        report_filter = ttypes.ReportFilter()
        add_filter_conditions(client, report_filter, args)

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
        run_filter = ttypes.RunFilter(names=args.names)
        run_ids = [run.runId for run in get_run_data(client, run_filter)]
        if not run_ids:
            LOG.warning("No runs were found!")
            sys.exit(1)

    all_checkers_report_filter = ttypes.ReportFilter()
    add_filter_conditions(client, all_checkers_report_filter, args)

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

    # Get severity counts
    report_filter = ttypes.ReportFilter()
    add_filter_conditions(client, report_filter, args)

    sev_count = client.getSeverityCounts(run_ids, report_filter, None)

    severities = []
    severity_total = 0
    for key, count in sorted(list(sev_count.items()),
                             reverse=True):
        severities.append(dict(
            severity=ttypes.Severity._VALUES_TO_NAMES[key],
            reports=count))
        severity_total += count

    all_results = []
    total = defaultdict(int)
    for key, checker_data in sorted(list(all_checkers_dict.items()),
                                    key=lambda x: x[1].severity,
                                    reverse=True):
        all_results.append(dict(
            checker=key,
            severity=ttypes.Severity._VALUES_TO_NAMES[checker_data.severity],
            reports=checker_data.count,
            unreviewed=checker_count(unrev_checkers, key),
            confirmed=checker_count(confirmed_checkers, key),
            false_positive=checker_count(false_checkers, key),
            intentional=checker_count(intentional_checkers, key)
        ))
        total['total_reports'] += checker_data.count
        total['total_unreviewed'] += checker_count(unrev_checkers, key)
        total['total_confirmed'] += checker_count(confirmed_checkers, key)
        total['total_false_positive'] += checker_count(false_checkers, key)
        total['total_intentional'] += checker_count(intentional_checkers, key)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(all_results))
    else:
        header = ['Checker', 'Severity', 'Unreviewed', 'Confirmed',
                  'False positive', 'Intentional', 'All reports']

        rows = []
        for stat in all_results:
            rows.append((stat['checker'],
                         stat['severity'],
                         str(stat['unreviewed']),
                         str(stat['confirmed']),
                         str(stat['false_positive']),
                         str(stat['intentional']),
                         str(stat['reports'])))

        rows.append(('Total', '-',
                     str(total['total_unreviewed']),
                     str(total['total_confirmed']),
                     str(total['total_false_positive']),
                     str(total['total_intentional']),
                     str(total['total_reports'])))

        print(twodim.to_str(args.output_format, header, rows,
                            separate_footer=True))

        # Print severity counts
        header = ['Severity', 'All reports']

        rows = []
        for stat in severities:
            rows.append((stat['severity'],
                         str(stat['reports'])))

        rows.append(('Total', str(severity_total)))

        print(twodim.to_str(args.output_format, header, rows,
                            separate_footer=True))


def handle_remove_run_results(args):

    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    run_filter = process_run_filter_conditions(args)
    if client.removeRun(None, run_filter):
        LOG.info("Done.")
    else:
        LOG.error("Failed to remove runs!")


def handle_update_run(args):
    """
    Argument handler for the 'CodeChecker cmd update' subcommand.
    """
    init_logger(args.verbose if 'verbose' in args else None)

    if not args.new_run_name:
        LOG.error("The new run name can not be empty!")
        sys.exit(1)

    client = setup_client(args.product_url)

    run_info = check_run_names(client, [args.run_name])
    run = run_info.get(args.run_name)
    if not run:
        LOG.warning("No run name with the name '%s' was found.", args.name)
        return

    try:
        client.updateRunData(run.runId, args.new_run_name)
    except RequestFailed as reqfail:
        LOG.error(reqfail.message)
        sys.exit(1)

    LOG.info("Done.")


def handle_suppress(args):

    init_logger(args.verbose if 'verbose' in args else None)

    limit = constants.MAX_QUERY_SIZE

    client = setup_client(args.product_url)

    run_info = check_run_names(client, [args.name])
    run = run_info.get(args.name)
    if not run:
        LOG.warning("No run name with the name '%s' was found.", args.name)
        return

    if 'input' in args:
        with open(args.input, encoding='utf-8', errors='ignore') as supp_file:
            suppress_data = suppress_file_handler.get_suppress_data(supp_file)

        for bug_id, file_name, comment, status in suppress_data:
            file_name = '%' + file_name
            bug_hash_filter = ttypes.ReportFilter(filepath=[file_name],
                                                  reportHash=[bug_id])
            reports = client.getRunResults([run.runId], limit, 0, None,
                                           bug_hash_filter,
                                           None, False)

            for report in reports:
                rw_status = ttypes.ReviewStatus.FALSE_POSITIVE
                if status == 'confirmed':
                    rw_status = ttypes.ReviewStatus.CONFIRMED
                elif status == 'intentional':
                    rw_status = ttypes.ReviewStatus.INTENTIONAL

                client.changeReviewStatus(report.reportId, rw_status, comment)


def handle_login(args):

    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    login_user(protocol, host, port, args.username,
               login='logout' not in args)


def handle_list_run_histories(args):
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    client = setup_client(args.product_url)
    run_ids = None
    if 'names' in args:
        run_filter = ttypes.RunFilter(names=args.names)
        runs = get_run_data(client, run_filter)
        run_ids = [r.runId for r in runs]

    run_history = client.getRunHistory(run_ids, None, None, None)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(run_history))
    else:  # plaintext, csv
        header = ['Date', 'Run name', 'Version tag', 'User',
                  'CodeChecker version', 'Analyzer statistics', 'Description']
        rows = []
        for h in run_history:
            analyzer_statistics = []
            for analyzer in h.analyzerStatistics:
                stat = h.analyzerStatistics[analyzer]
                num_of_all_files = stat.successful + stat.failed
                analyzer_statistics.append(analyzer + ' (' +
                                           str(num_of_all_files) + '/' +
                                           str(stat.successful) + ')')

            rows.append((h.time,
                         h.runName,
                         h.versionTag if h.versionTag else '',
                         h.user,
                         h.codeCheckerVersion if h.codeCheckerVersion else '',
                         ', '.join(analyzer_statistics),
                         h.description if h.description else ''))

        print(twodim.to_str(args.output_format, header, rows))


def handle_export(args):

    stream = 'stderr'
    init_logger(args.verbose if 'verbose' in args else None, stream)

    client = setup_client(args.product_url)
    run_filter = process_run_filter_conditions(args)

    runs = get_run_data(client, run_filter)
    if not runs:
        LOG.warning("No runs found")
        sys.exit(1)

    report = client.exportData(run_filter)
    print(CmdLineOutputEncoder().encode(report))


def handle_import(args):
    """
    Argument handler for the 'CodeChecker cmd import' subcommand
    """

    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    data = util.load_json_or_empty(args.input, default=None)
    if not data:
        LOG.error("Failed to import data!")
        sys.exit(1)

    # Convert Json comments into CommentDataList
    comment_data_list = defaultdict(list)
    for bug_hash, comments in data['comments'].items():
        for comment in comments:
            comment_data = ttypes.CommentData(
                id=comment['id'],
                author=comment['author'],
                message=comment['message'],
                createdAt=comment['createdAt'],
                kind=comment['kind'])
            comment_data_list[bug_hash].append(comment_data)

    # Convert Json reviews into ReviewData
    review_data_list = {}
    for bug_hash, review in data['reviewData'].items():
        review_data_list[bug_hash] = ttypes.ReviewData(
            status=review['status'],
            comment=review['comment'],
            author=review['author'],
            date=review['date'])

    exportData = ttypes.ExportData(comments=comment_data_list,
                                   reviewData=review_data_list)

    status = client.importData(exportData)
    if not status:
        LOG.error("Failed to import data!")
        sys.exit(1)

    LOG.info("Import successful!")
