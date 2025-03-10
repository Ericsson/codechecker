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
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import os
import re
import sys
import shutil
import time
import json
from typing import Dict, Iterable, List, Optional, Set, Tuple

from codechecker_api.codeCheckerDBAccess_v6 import constants, ttypes
from codechecker_api_shared.ttypes import RequestFailed

from codechecker_report_converter import twodim
from codechecker_report_converter.report import File, Report, report_file, \
    reports as reports_helper
from codechecker_report_converter.report.output import baseline, codeclimate, \
    gerrit, json as report_to_json, plaintext
from codechecker_report_converter.report.output.html import \
    html as report_to_html
from codechecker_report_converter.report.statistics import Statistics
from codechecker_report_converter.util import dump_json_output

from codechecker_common import logger
from codechecker_common.checker_labels import CheckerLabels
from codechecker_common.review_status_handler import ReviewStatusHandler
from codechecker_common.util import load_json

from codechecker_web.shared import convert, webserver_context

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


def run_sort_type_str(value: ttypes.RunSortType) -> Optional[str]:
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

    assert False, f"Unknown ttypes.RunSortType: {value}"


def run_sort_type_enum(value: str) -> Optional[ttypes.RunSortType]:
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

    assert False, f"Unknown ttypes.RunSortType value: {str}"


def get_diff_type(args) -> ttypes.DiffType:
    """
    Returns Thrift DiffType value by processing the arguments.
    """
    if 'new' in args:
        return ttypes.DiffType.NEW
    elif 'unresolved' in args:
        return ttypes.DiffType.UNRESOLVED
    elif 'resolved' in args:
        return ttypes.DiffType.RESOLVED

    assert False, "Unknown ttypes.DiffType: {args}"


def get_run_tag(client, run_ids: List[int], tag_name: str):
    """Return run tag information for the given tag name in the given runs."""
    run_history_filter = ttypes.RunHistoryFilter()
    run_history_filter.tagNames = [tag_name]
    run_histories = client.getRunHistory(run_ids, None, None,
                                         run_history_filter)

    return run_histories[0] if run_histories else None


def process_run_args(client, run_args_with_tag: Iterable[str]):
    """Process the argument and returns run ids and run tag ids.

    The elemnts inside the given run_args_with_tag list has the following
    format: `<run_name>:<run_tag>`.
    If the run name is containing a literal ':', it should be escaped with a
    backslash escape character before the `:`.
    """
    # (The documentation comment above means \:, but Python would want to
    # understand that as an escape sequence immediately.)

    run_ids = []
    run_names = []
    run_tags = []

    for run_arg_with_tag in run_args_with_tag:
        run_with_tag = list(map(lambda n: n.replace(r"\:", ":"),
                                re.split(r"(?<!\\):", run_arg_with_tag)))
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
                           review_st: List[ttypes.ReviewStatus]) -> List[str]:
    """Returns a list of suppressed report hashes."""
    statuses_str = [ttypes.ReviewStatus._VALUES_TO_NAMES[x].lower()
                    for x in review_st]

    return [
        report.report_hash for report in reports
        if report.review_status.status != 'unreviewed' and
        report.review_status not in statuses_str]


def get_report_dir_results(
    report_dirs: List[str],
    report_filter: ttypes.ReportFilter,
    checker_labels: CheckerLabels
) -> List[Report]:
    """Get reports from the given report directories.

    Absolute paths are expected to the given report directories.
    """
    all_reports = []

    processed_path_hashes = set()
    for report_dir, file_paths in \
            report_file.analyzer_result_files(report_dirs):

        review_status_handler = ReviewStatusHandler()
        review_status_cfg = os.path.join(report_dir, 'review_status.yaml')
        if os.path.isfile(review_status_cfg):
            try:
                review_status_handler.set_review_status_config(
                    review_status_cfg)
            except ValueError as err:
                LOG.error(err)
                sys.exit(1)

        for file_path in file_paths:
            # Get reports.
            reports = report_file.get_reports(file_path, checker_labels)

            try:
                for report in reports:
                    report.review_status = \
                        review_status_handler.get_review_status(report)
            except ValueError as err:
                LOG.error(err)

            # Skip duplicated reports.
            reports = reports_helper.skip(reports, processed_path_hashes)

            # Skip reports based on filter arguments.
            reports = [report for report in reports
                       if not skip_report_dir_result(
                           report, report_filter, checker_labels)]

            all_reports.extend(reports)

    return all_reports


def skip_report_dir_result(
    report: Report,
    report_filter: ttypes.ReportFilter,
    checker_labels: CheckerLabels
) -> bool:
    """Returns True if the report should be skipped from the results.

    Skipping is done based on the given filter set.
    """

    if report_filter.severity:
        severity_name = checker_labels.severity(report.checker_name)
        filter_severities_str = [ttypes.Severity._VALUES_TO_NAMES[x]
                                 for x in report_filter.severity]
        if severity_name.lower() not in \
                list(map(str.lower, filter_severities_str)):
            return True

    if report_filter.checkerName:
        checker_name = report.checker_name
        if not any(re.match(r'^' + c.replace("*", ".*") + '$',
                            checker_name, re.IGNORECASE)
                   for c in report_filter.checkerName):
            return True

    if report_filter.filepath:
        if not any(re.match(r'^' + f.replace("*", ".*") + '$',
                            report.file.path, re.IGNORECASE)
                   for f in report_filter.filepath):
            return True

    if report_filter.checkerMsg:
        checker_msg = report.message
        if not any(re.match(r'^' + c.replace("*", ".*") + '$',
                            checker_msg, re.IGNORECASE)
                   for c in report_filter.checkerMsg):
            return True

    return False


def get_diff_base_results(
    client,
    report_filter: ttypes.ReportFilter,
    baseids,
    base_hashes,
    suppressed_hashes,
    get_details: bool = True
):
    """Get the run results from the server."""
    report_filter.reportHash = base_hashes + suppressed_hashes
    report_filter.reviewStatus = [
        ttypes.ReviewStatus.UNREVIEWED,
        ttypes.ReviewStatus.CONFIRMED]

    sort_mode = [(ttypes.SortMode(
        ttypes.SortType.FILENAME,
        ttypes.Order.ASC))]

    limit = constants.MAX_QUERY_SIZE
    offset = 0

    base_results = []
    while True:
        results = client.getRunResults(
            baseids, limit, offset, sort_mode, report_filter, None,
            get_details)

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


def check_existing_source_components(
    client,
    source_components: List[str]
):
    missing_source_components = []

    for source_component in source_components:
        if not client.getSourceComponents([source_component]):
            missing_source_components.append(source_component)

    if missing_source_components:
        LOG.error(
            "The following source components don't exist: %s",
            ', '.join(missing_source_components))
        sys.exit(1)


def check_deprecated_arg_usage(args):
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


def validate_filter_values(converted_values: List[int], valid_values,
                           value_type):
    """
    Check if the value provided by the user is a valid value.
    """
    # Can be None if the user provided no value to this option -- that is
    # valid.
    if not converted_values:
        return True

    non_valid_values = [status for status in converted_values
                        if valid_values.get(status, None) is None]

    if non_valid_values:
        invalid_values = ','.join([x.lower() for x in non_valid_values])
        LOG.error('Invalid %s value(s): %s', value_type, invalid_values)

        valid_values = ','.join([x.lower() for x in valid_values.keys()])
        LOG.error('Valid values are: %s', valid_values)

        return False

    return True


def parse_report_filter(client, args):
    """
    Parse and check attributes of the given report filter based on
    the arguments which is provided in the command line.
    Also, check if filter values are valid values.
    """
    report_filter = parse_report_filter_offline(args)

    if 'tag' in args:
        run_history_filter = ttypes.RunHistoryFilter(tagNames=args.tag)
        run_histories = client.getRunHistory(None, None, None,
                                             run_history_filter)
        if run_histories:
            report_filter.runTag = [t.id for t in run_histories]

    return report_filter


def parse_report_filter_offline(args):
    """
    Same as parse_report_filter, but will not make calls to the server.
    As of writing this comment, this means that the 'tag' argument will be
    ignored (as that would require a getRunHistory API call).
    """
    report_filter = ttypes.ReportFilter()

    if 'severity' in args:
        report_filter.severity = [
            ttypes.Severity._NAMES_TO_VALUES[x.upper()] for x in args.severity]

    if 'detection_status' in args:
        report_filter.detectionStatus = [
            ttypes.DetectionStatus._NAMES_TO_VALUES[x.upper()] for x in
            args.detection_status]

    if 'review_status' in args:
        report_filter.reviewStatus = [
            ttypes.ReviewStatus._NAMES_TO_VALUES[x.upper()] for x in
            args.review_status]

    if 'checker_name' in args:
        report_filter.checkerName = args.checker_name

    if 'file_path' in args:
        report_filter.filepath = args.file_path

    if 'bug_path_length' in args:
        path_lengths = args.bug_path_length.split(':')

        min_bug_path_length = int(path_lengths[0]) if \
            path_lengths and path_lengths[0].isdigit() else None

        max_bug_path_length = int(path_lengths[1]) if \
            len(path_lengths) > 1 and path_lengths[1].isdigit() else None

        report_filter.bugPathLength = \
            BugPathLengthRange(min=min_bug_path_length,
                               max=max_bug_path_length)

    values_to_check = [
        (report_filter.severity, ttypes.Severity._VALUES_TO_NAMES, 'severity'),
        (report_filter.detectionStatus,
         ttypes.DetectionStatus._VALUES_TO_NAMES,
         'detection status'),
        (report_filter.reviewStatus, ttypes.ReviewStatus._VALUES_TO_NAMES,
         'review status')]

    if not all(valid for valid in
               [validate_filter_values(*x) for x in values_to_check]):
        sys.exit(1)

    report_filter.isUnique = args.uniqueing == 'on'

    if 'checker_msg' in args:
        report_filter.checkerMsg = args.checker_msg

    if 'analyzer_name' in args:
        report_filter.analyzerNames = args.analyzer_name

    if 'component' in args:
        report_filter.componentNames = args.component

    if 'report_hash' in args:
        report_filter.reportHash = args.report_hash

    if 'open_reports_date' in args:
        report_filter.openReportsDate = \
            int(str_to_timestamp(args.open_reports_date))

    detected_at = None
    fixed_at = None

    if 'detected_at' in args:
        report_filter.firstDetectionDate = \
            int(str_to_timestamp(args.detected_at))

    if 'fixed_at' in args:
        report_filter.fixDate = int(str_to_timestamp(args.fixed_at))

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

    report_filter.fileMatchesAnyPoint = args.anywhere_on_report_path
    report_filter.componentMatchesAnyPoint = args.anywhere_on_report_path

    if args.anywhere_on_report_path and \
            'file_path' not in args and 'component' not in args:
        LOG.warning(
            'The flag --anywhere-on-report-path is meaningful only if --file '
            'or --component is used.')

    return report_filter


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

    if hasattr(args, 'enabled_checkers') and args.enabled_checkers:
        enabled_checkers: Dict[str, List[str]] = {}
        for run in runs:
            info_list: List[ttypes.AnalysisInfo] = client.getAnalysisInfo(
                ttypes.AnalysisInfoFilter(runId=run.runId),
                constants.MAX_QUERY_SIZE,
                0)
            for info in info_list:
                analyzers = info.checkers.keys()
                for analyzer in analyzers:
                    if analyzer not in enabled_checkers:
                        enabled_checkers[analyzer] = []

                    checkers = info.checkers.get(analyzer, {})
                    for checker in checkers:
                        if checkers[checker].enabled:
                            enabled_checkers[analyzer].append(checker)

        if args.output_format == 'plaintext':
            for analyzer, checkers in enabled_checkers.items():
                print(analyzer + ":")
                for checker in checkers:
                    print("  " + checker)
        elif args.output_format == 'csv':
            separator = ';'
            print("Analyzer" + separator + "Checker")
            for analyzer, checkers in enabled_checkers.items():
                for checker in checkers:
                    print(analyzer + separator + checker)
        elif args.output_format == 'json':
            print(json.dumps(enabled_checkers, indent=4))
        elif args.output_format == 'table':
            header = ['Analyzer', 'Checker']
            rows = [
                (analyzer, checker)
                for analyzer, checkers in enabled_checkers.items()
                for checker in checkers]
            print(twodim.to_str(args.output_format, header, rows))
        else:
            LOG.error("Unsupported output format: %s", args.output_format)
        return

    if args.output_format == 'json':
        # This json is different from the json format printed by the
        # parse command. This json converts the ReportData type report
        # to a json format.
        results = []
        for run in runs:
            if 'details' in args and args.details:
                run.analyzerStatistics = \
                    client.getAnalysisStatistics(run.runId, None)
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
    return


def handle_list_results(args):
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    check_deprecated_arg_usage(args)

    client = setup_client(args.product_url)

    if 'component' in args:
        check_existing_source_components(client, args.component)

    run_filter = ttypes.RunFilter(names=args.names)

    run_data = get_run_data(client, run_filter)
    run_ids = [run.runId for run in run_data]
    if not run_ids:
        LOG.warning("No runs were found!")
        sys.exit(1)

    report_filter = parse_report_filter(client, args)

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
        if 'details' in args:
            run_id2name = {run.runId: run.name for run in run_data}
            for report in all_results:
                report.runName = run_id2name[report.runId]

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


def get_source_line_contents(
    client,
    reports: List[ttypes.ReportData]
) -> Dict[int, Dict[int, str]]:
    """
    Get source line contents from the server for the given report data.
    """
    source_lines = defaultdict(set)
    for report_data in reports:
        source_lines[report_data.fileId].add(report_data.line)

    lines_in_files_requested = []
    for file_id in source_lines:
        lines_in_files_requested.append(
            ttypes.LinesInFilesRequested(fileId=file_id,
                                         lines=source_lines[file_id]))

    return client.getLinesInSourceFileContents(
        lines_in_files_requested, ttypes.Encoding.BASE64)


def convert_report_data_to_report(
    client,
    reports_data: List[ttypes.ReportData],
    output_formats: List[str]
) -> List[Report]:
    """
    Convert the given report data list to local reports.

    If one of the given output format is HTML it will get full source file
    contents from the server otherwise for performance reason it will
    get only necessarry line contents.
    """
    reports = []

    if not reports_data:
        return reports

    source_line_contents = {}
    if 'html' not in output_formats:
        source_line_contents = get_source_line_contents(client, reports_data)

    file_cache: Dict[int, File] = {}

    def cached_report_file_lookup(file_id: int, file_path: str) -> File:
        """
        It will create a file object with the given 'file_path' attribute if
        file data is not found in the cache already based on the following
        conditions:
          - if HTML output is given it will try to get source file data for the
            given file id from the server and set the content attribute of the
            file object. File content is needed only by the HTML output
            converter.
          - otherwise it will create a file object where file content will not
            be filled automatically but will be loaded from the host machine
            when it is needed.

        Finally, it returns the source file data from the cache.
        """
        nonlocal file_cache

        if file_id not in file_cache:
            file_cache[file_id] = File(file_path, file_id)

            if 'html' in output_formats:
                source = client.getSourceFileData(
                    file_id, True, ttypes.Encoding.BASE64)
                file_cache[file_id].content = convert.from_b64(
                    source.fileContent)

        return file_cache[file_id]

    # Convert reports data to reports.
    for report_data in reports_data:
        report = report_type_converter.to_report(
            report_data, cached_report_file_lookup)

        report.changed_files = []
        report.source_code_comments = []

        if source_line_contents:
            source_line = convert.from_b64(
                source_line_contents[report_data.fileId][report_data.line])
            report.source_line = f"{source_line}{os.linesep}"

        reports.append(report)

    return reports


def get_diff_local_dir_remote_run(
    client,
    report_filter: ttypes.ReportFilter,
    diff_type: ttypes.DiffType,
    output_formats: List[str],
    report_dirs: List[str],
    baseline_files: List[str],
    remote_run_names: List[str]
) -> Tuple[List[Report], List[str], List[str]]:
    """ Compare a local report directory with a remote run. """
    filtered_reports = []
    filtered_report_hashes: Set[str] = set()

    context = webserver_context.get_context()
    report_dir_results = get_report_dir_results(
        report_dirs, report_filter, context.checker_labels)

    suppressed_in_code = \
        get_suppressed_reports(report_dir_results, report_filter.reviewStatus)

    run_ids, run_names, tag_ids = \
        process_run_args(client, remote_run_names)
    local_report_hashes = set(r.report_hash for r in report_dir_results)

    review_status_filter = ttypes.ReviewStatusRuleFilter()
    review_status_filter.reportHashes = local_report_hashes
    review_status_filter.reviewStatuses = [
        ttypes.ReviewStatus.FALSE_POSITIVE,
        ttypes.ReviewStatus.INTENTIONAL]
    closed_hashes = set(
        rule.reportHash for rule in
        client.getReviewStatusRules(
            review_status_filter, None, None, None))

    report_dir_results = [
        r for r in report_dir_results if
        r.review_status.status not in ['false_positive', 'intentional'] and
        (r.report_hash not in closed_hashes or
         r.review_status.status == 'confirmed')]
    local_report_hashes = set(r.report_hash for r in report_dir_results)
    local_report_hashes.update(
        baseline.get_report_hashes(baseline_files) - closed_hashes)

    if diff_type == ttypes.DiffType.NEW:
        # Get report hashes which can be found only in the remote runs.
        remote_hashes = client.getDiffResultsHash(
            run_ids, local_report_hashes, ttypes.DiffType.RESOLVED,
            None, tag_ids)

        results = get_diff_base_results(
            client, report_filter, run_ids, remote_hashes, suppressed_in_code)

        filtered_reports.extend(
            convert_report_data_to_report(client, results, output_formats))
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
                client, report_filter, run_ids, list(filtered_report_hashes),
                suppressed_in_code)

            for result in results:
                filtered_report_hashes.discard(result.bugHash)

            filtered_reports.extend(
                convert_report_data_to_report(client, results, output_formats))
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
    report_filter: ttypes.ReportFilter,
    diff_type: ttypes.DiffType,
    output_formats: List[str],
    remote_run_names: List[str],
    report_dirs: List[str],
    baseline_files: List[str]
) -> Tuple[List[Report], List[str], List[str]]:
    """ Compares a remote run with a local report directory. """
    filtered_reports = []
    filtered_report_hashes = []

    context = webserver_context.get_context()
    report_dir_results = get_report_dir_results(
        report_dirs, report_filter, context.checker_labels)
    suppressed_in_code = \
        get_suppressed_reports(report_dir_results, report_filter.reviewStatus)

    run_ids, run_names, tag_ids = \
        process_run_args(client, remote_run_names)
    local_report_hashes = set(r.report_hash for r in report_dir_results)

    review_status_filter = ttypes.ReviewStatusRuleFilter()
    review_status_filter.reportHashes = local_report_hashes
    review_status_filter.reviewStatuses = [
        ttypes.ReviewStatus.FALSE_POSITIVE,
        ttypes.ReviewStatus.INTENTIONAL]
    closed_hashes = set(
        rule.reportHash for rule in
        client.getReviewStatusRules(
            review_status_filter, None, None, None))

    report_dir_results = [
        r for r in report_dir_results if
        r.review_status.status not in ['false_positive', 'intentional'] and
        (r.report_hash not in closed_hashes or
         r.review_status.status == 'confirmed')]

    local_report_hashes = set(r.report_hash for r in report_dir_results)
    local_report_hashes.update(
        baseline.get_report_hashes(baseline_files) - closed_hashes)

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
            client, report_filter, run_ids, remote_hashes, suppressed_in_code)

        filtered_reports.extend(
            convert_report_data_to_report(client, results, output_formats))

    return filtered_reports, filtered_report_hashes, run_names


def get_diff_remote_runs(
    client,
    report_filter: ttypes.ReportFilter,
    diff_type: ttypes.DiffType,
    output_formats: List[str],
    remote_base_run_names: Iterable[str],
    remote_new_run_names: Iterable[str]
) -> Tuple[List[Report], List[str], List[str]]:
    """
    Compares two remote runs and returns the filtered results.
    """
    base_ids, base_run_names, base_run_tags = \
        process_run_args(client, remote_base_run_names)
    report_filter.runTag = base_run_tags

    cmp_data = ttypes.CompareData()
    cmp_data.diffType = diff_type

    new_ids, new_run_names, new_run_tags = \
        process_run_args(client, remote_new_run_names)
    cmp_data.runIds = new_ids
    cmp_data.runTag = new_run_tags

    sort_mode = [(ttypes.SortMode(
        ttypes.SortType.FILENAME,
        ttypes.Order.ASC))]

    # Generally speaking, we only compare outstanding reports in both the
    # baseline and newline analyses, so it wouldn't make sense to show reports
    # whose detection status indicates otherwise. However, for tags, we check
    # whether a report is outstanding at the time of the tag, so in the context
    # of that tag, a resolved report may actually be outstanding, so we clear
    # the detection status filter.
    # TODO: We don't support diffs with timestamps on the cmdline, but we
    # should do this for them as well.
    if base_run_tags or new_run_tags:
        # If the value is not the default, lets warn the user that we overwrote
        # it.
        default_detection_status = [ttypes.DetectionStatus.NEW,
                                    ttypes.DetectionStatus.REOPENED,
                                    ttypes.DetectionStatus.UNRESOLVED]
        if report_filter.detectionStatus not in (default_detection_status, []):
            LOG.warning("--detection-status is ignored when comparing tags, "
                        "showing reports regardless of detection status.")

        report_filter.detectionStatus = []

    all_results = get_run_results(
        client, base_ids, constants.MAX_QUERY_SIZE, 0, sort_mode,
        report_filter, cmp_data, True)

    reports = \
        convert_report_data_to_report(client, all_results, output_formats)
    return reports, base_run_names, new_run_names


def get_diff_local_dirs(
    report_filter: ttypes.ReportFilter,
    diff_type: ttypes.DiffType,
    # TODO: No output_format argument? How come? Maybe the other functions
    # don't need it either?
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

    context = webserver_context.get_context()
    statuses_str = [ttypes.ReviewStatus._VALUES_TO_NAMES[x].lower()
                    for x in report_filter.reviewStatus]
    statuses_str.append('unreviewed')

    base_results = get_report_dir_results(
        report_dirs, report_filter, context.checker_labels)
    base_results = [res for res in base_results
                    if res.review_status.status in statuses_str]

    new_results = get_report_dir_results(
        new_report_dirs, report_filter, context.checker_labels)
    new_results = [res for res in new_results
                   if res.review_status.status in statuses_str]

    base_hashes = set(res.report_hash for res in base_results)
    new_hashes = set(res.report_hash for res in new_results)

    # Add hashes from the baseline files.
    base_hashes.update(baseline.get_report_hashes(baseline_files))
    new_hashes.update(baseline.get_report_hashes(new_baseline_files))

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


def print_reports(
    print_steps: bool,
    reports: List[Report],
    report_hashes: Iterable[str],
    output_dir: str,
    output_formats: List[str]
):
    if report_hashes:
        LOG.info("Couldn't get local reports for the following baseline "
                 "report hashes: %s", ', '.join(sorted(report_hashes)))

    statistics = Statistics()
    changed_files: Set[str] = set()
    html_builder: Optional[report_to_html.HtmlBuilder] = None
    for report in reports:
        statistics.add_report(report)

        if report.changed_files:
            changed_files.update(report.changed_files)

        repo_dir = os.environ.get('CC_REPO_DIR')
        if repo_dir:
            report.trim_path_prefixes([repo_dir])

    processed_file_paths = set()
    for output_format in output_formats:
        if output_format == 'plaintext':
            file_report_map = plaintext.get_file_report_map(reports)
            plaintext.convert(
                ReviewStatusHandler(),
                file_report_map, processed_file_paths, print_steps)

        context = webserver_context.get_context()
        if output_format == 'html':
            if not html_builder:
                html_builder = report_to_html.HtmlBuilder(
                    context.path_plist_to_html_dist,
                    context.checker_labels)

            file_report_map = plaintext.get_file_report_map(reports)

            LOG.info("Generating HTML output files to file://%s "
                     "directory:", output_dir)

            for file_path, file_reports in file_report_map.items():
                file_name = os.path.basename(file_path)
                h = int(
                    hashlib.md5(
                        file_path.encode('utf-8')).hexdigest(),
                    16) % (10 ** 8)

                output_file_path = os.path.join(
                    output_dir, f"{file_name}_ {str(h)}.html")
                html_builder.create(output_file_path, file_reports)

        if output_format in ['csv', 'rows', 'table']:
            header = ['File', 'Checker', 'Severity', 'Msg', 'Source']
            rows = []
            for report in reports:
                if report.source_line is None:
                    continue

                checked_file = f"{report.file.path}:{str(report.line)}:" \
                               f"{str(report.column)}"
                rows.append((
                    report.severity,
                    checked_file,
                    report.message,
                    report.checker_name,
                    report.source_line.rstrip()))

            print(twodim.to_str(output_format, header, rows))

        if output_format == 'json':
            data = report_to_json.convert(reports)

            report_json = os.path.join(output_dir, 'reports.json') \
                if output_dir else None
            dump_json_output(data, report_json)

        if output_format == 'gerrit':
            data = gerrit.convert(reports)

            report_json = os.path.join(
                output_dir, 'gerrit_review.json') if output_dir else None
            dump_json_output(data, report_json)

        if output_format == 'codeclimate':
            data = codeclimate.convert(reports)

            report_json = os.path.join(
                output_dir, 'codeclimate_issues.json') \
                if output_dir else None
            dump_json_output(data, report_json)

    if 'html' in output_formats:
        html_builder.finish(output_dir, statistics)

    if 'plaintext' in output_formats:
        statistics.write()

    reports_helper.dump_changed_files(changed_files)


def handle_diff_results(args):
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    output_formats = args.output_format
    if output_formats != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    output_dir = args.export_dir if 'export_dir' in args else None
    if len(output_formats) > 1 and ('export_dir' not in args):
        LOG.error("Export directory is required if multiple output formats "
                  "are selected!")
        sys.exit(1)

    if 'html' in output_formats and not output_dir:
        LOG.error("Argument --export not allowed without argument --output "
                  "when exporting to HTML.")
        sys.exit(1)

    if 'gerrit' in output_formats and \
            not gerrit.mandatory_env_var_is_set():
        sys.exit(1)

    check_deprecated_arg_usage(args)

    if 'clean' in args and os.path.isdir(output_dir):
        print(f"Previous analysis results in '{output_dir}' have been "
              "removed, overwriting with current results.")
        shutil.rmtree(output_dir)

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    client = None

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

    if 'component' in args:
        check_existing_source_components(client, args.component)

    print_steps = 'print_steps' in args
    report_hashes = []
    if (basename_local_dirs or basename_baseline_files) and \
       (newname_local_dirs or newname_baseline_files):
        report_filter = parse_report_filter_offline(args)
        diff_type = get_diff_type(args)

        reports, report_hashes = get_diff_local_dirs(
            report_filter, diff_type,
            basename_local_dirs, basename_baseline_files,
            newname_local_dirs, newname_baseline_files)

        print_reports(print_steps, reports, report_hashes, output_dir,
                      output_formats)
        LOG.info("Compared the following local files / directories: %s and %s",
                 ', '.join([*basename_local_dirs, *basename_baseline_files]),
                 ', '.join([*newname_local_dirs, *newname_baseline_files]))
    elif newname_local_dirs or newname_baseline_files:
        report_filter = parse_report_filter(client, args)
        diff_type = get_diff_type(args)

        reports, report_hashes, matching_base_run_names = \
            get_diff_remote_run_local_dir(
                client, report_filter, diff_type, output_formats,
                basename_run_names,
                newname_local_dirs, newname_baseline_files)

        print_reports(print_steps, reports, report_hashes, output_dir,
                      output_formats)
        LOG.info("Compared remote run(s) %s (matching: %s) and local files / "
                 "report directory(s) %s",
                 ', '.join(basename_run_names),
                 ', '.join(matching_base_run_names),
                 ', '.join([*newname_local_dirs, *newname_baseline_files]))
    elif (basename_local_dirs or basename_baseline_files):
        report_filter = parse_report_filter(client, args)
        diff_type = get_diff_type(args)

        reports, report_hashes, matching_new_run_names = \
            get_diff_local_dir_remote_run(
                client, report_filter, diff_type, output_formats,
                basename_local_dirs,
                basename_baseline_files, newname_run_names)

        print_reports(print_steps, reports, report_hashes, output_dir,
                      output_formats)
        LOG.info("Compared local files / report directory(s) %s and remote "
                 "run(s) %s (matching: %s).",
                 ', '.join([*basename_local_dirs, *basename_baseline_files]),
                 ', '.join(newname_run_names),
                 ', '.join(matching_new_run_names))
    else:
        report_filter = parse_report_filter(client, args)
        diff_type = get_diff_type(args)

        reports, matching_base_run_names, matching_new_run_names = \
            get_diff_remote_runs(
                client, report_filter, diff_type, output_formats,
                basename_run_names, newname_run_names)
        print_reports(print_steps, reports, None, output_dir, output_formats)
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

    def get_statistics(
        client, run_ids, field, values,
        all_checkers_report_filter
    ):
        report_filter = deepcopy(all_checkers_report_filter)

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

    if 'component' in args:
        check_existing_source_components(client, args.component)

    run_ids = None
    if 'all_results' not in args:
        run_filter = ttypes.RunFilter(names=args.names)
        run_ids = [run.runId for run in get_run_data(client, run_filter)]
        if not run_ids:
            LOG.warning("No runs were found!")
            sys.exit(1)

    all_checkers_report_filter = parse_report_filter(client, args)

    all_checkers = client.getCheckerCounts(run_ids,
                                           all_checkers_report_filter,
                                           None,
                                           None,
                                           0)
    all_checkers_dict = dict((res.name, res) for res in all_checkers)

    unrev_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                    [ttypes.ReviewStatus.UNREVIEWED],
                                    all_checkers_report_filter)

    confirmed_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                        [ttypes.ReviewStatus.CONFIRMED],
                                        all_checkers_report_filter)

    false_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                    [ttypes.ReviewStatus.FALSE_POSITIVE],
                                    all_checkers_report_filter)

    intentional_checkers = get_statistics(client, run_ids, 'reviewStatus',
                                          [ttypes.ReviewStatus.INTENTIONAL],
                                          all_checkers_report_filter)

    # Get severity counts
    sev_count = client.getSeverityCounts(
        run_ids, all_checkers_report_filter, None)

    severities = []
    severity_total = 0
    for key, count in sorted(list(sev_count.items()), reverse=True):
        severities.append({
            "severity": ttypes.Severity._VALUES_TO_NAMES[key],
            "reports": count
        })
        severity_total += count

    all_results = []
    total = defaultdict(int)
    for key, checker_data in sorted(list(all_checkers_dict.items()),
                                    key=lambda x: x[1].severity,
                                    reverse=True):
        all_results.append({
            "checker": key,
            "severity":
            ttypes.Severity._VALUES_TO_NAMES[checker_data.severity],
            "reports": checker_data.count,
            "unreviewed": checker_count(unrev_checkers, key),
            "confirmed": checker_count(confirmed_checkers, key),
            "false_positive": checker_count(false_checkers, key),
            "intentional": checker_count(intentional_checkers, key)
        })
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
        LOG.warning(
            "No runs were removed, check if the given criteria match existing "
            "run names.")


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

    data = load_json(args.input, default=None)
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

    export_data = ttypes.ExportData(
        comments=comment_data_list,
        reviewData=review_data_list)

    status = client.importData(export_data)
    if not status:
        LOG.error("Failed to import data!")
        sys.exit(1)

    LOG.info("Import successful!")
