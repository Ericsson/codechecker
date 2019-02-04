# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Command line client.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import base64
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import io
import os
import re
import sys
import shutil
import time

from plist_to_html import PlistToHtml

from codeCheckerDBAccess_v6 import constants, ttypes

from libcodechecker import package_context
from libcodechecker import logger
from libcodechecker import suppress_file_handler
from libcodechecker.analyze import plist_parser
from libcodechecker.libclient.client import handle_auth
from libcodechecker.libclient.client import setup_client
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.report import Report, get_report_path_hash
from libcodechecker.source_code_comment_handler import SourceCodeCommentHandler
from libcodechecker.util import split_server_url, CmdLineOutputEncoder


# Needs to be set in the handler functions.
LOG = None


def init_logger(level, logger_name='system'):
    logger.setup_logger(level)
    global LOG
    LOG = logger.get_logger(logger_name)


def str_to_timestamp(date_str):
    """
    Return timestamp parsed from the given string parameter.
    """
    dateformat = '%Y-%m-%d %H:%M:%S.%f'
    date_time = date_str if isinstance(date_str, datetime) else \
        datetime.strptime(date_str, dateformat)

    return time.mktime(date_time.timetuple())


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
            LOG.warning("The run named '%s' was not found.", name)
            missing_name = True

    if missing_name:
        print("Possible run names are:")
        for name, _ in run_info.items():
            print(name)
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


def get_runs(client, run_names):
    run_filter = ttypes.RunFilter()
    run_filter.names = run_names

    return client.getRunData(run_filter)


def validate_filter_values(user_values, valid_values, value_type):
    """
    Check if the value provided by the user is a valid value.
    """
    if not user_values:
        return True

    non_valid_values = [status for status in user_values
                        if valid_values.get(status.upper(), None) is None]

    if non_valid_values:
        invalid_values = ','.join(map(lambda x: x.lower(), non_valid_values))
        LOG.error('Invalid %s value(s): %s', value_type, invalid_values)

        valid_values = ','.join(map(lambda x: x.lower(), valid_values.keys()))
        LOG.error('Valid values are: %s', valid_values)

        return False

    return True


def check_filter_values(args):
    """
    Check if filter values are valid values. Returns values which are checked
    or exit from the interpreter.
    """
    severities = checkers = file_path = dt_statuses = rw_statuses = None

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

    values_to_check = [
        (severities, ttypes.Severity._NAMES_TO_VALUES, 'severity'),
        (dt_statuses, ttypes.DetectionStatus._NAMES_TO_VALUES,
         'detection status'),
        (rw_statuses, ttypes.ReviewStatus._NAMES_TO_VALUES,
         'review status')]

    if not all(valid for valid in
               [validate_filter_values(*x) for x in values_to_check]):
        sys.exit(1)
    return severities, checkers, file_path, dt_statuses, rw_statuses


def add_filter_conditions(client, report_filter, args):
    """
    This function fills some attributes of the given report filter based on
    the arguments which is provided in the command line.
    """

    severities, checkers, file_path, dt_statuses, rw_statuses = \
        check_filter_values(args)

    report_filter.isUnique = args.uniqueing == 'on'

    if severities:
        report_filter.severity = map(
                lambda x: ttypes.Severity._NAMES_TO_VALUES[x.upper()],
                severities)

    if dt_statuses:
        report_filter.detectionStatus = map(
            lambda x: ttypes.DetectionStatus._NAMES_TO_VALUES[x.upper()],
            dt_statuses)

    if rw_statuses:
        report_filter.reviewStatus = map(
            lambda x: ttypes.ReviewStatus._NAMES_TO_VALUES[x.upper()],
            rw_statuses)

    if checkers:
        report_filter.checkerName = checkers

    if 'checker_msg' in args:
        report_filter.checkerMsg = args.checker_msg

    if 'component' in args:
        report_filter.componentNames = args.component

    if 'report_hash' in args:
        report_filter.reportHash = args.report_hash

    if file_path:
        report_filter.filepath = file_path

    if 'tag' in args:
        run_history_filter = ttypes.RunHistoryFilter(tagNames=args.tag)
        run_histories = client.getRunHistory(None, None, None,
                                             run_history_filter)
        if run_histories:
            report_filter.runTag = [t.id for t in run_histories]

    if 'detected_at' in args:
        report_filter.firstDetectionDate = \
            int(str_to_timestamp(args.detected_at))

    if 'fixed_at' in args:
        report_filter.fixDate = int(str_to_timestamp(args.fixed_at))

# ---------------------------------------------------------------------------
# Argument handlers for the 'CodeChecker cmd' subcommands.
# ---------------------------------------------------------------------------


def handle_list_runs(args):

    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    run_filter = None
    if 'names' in args:
        run_filter = ttypes.RunFilter()
        run_filter.names = args.names

    runs = client.getRunData(run_filter)

    if args.output_format == 'json':
        results = []
        for run in runs:
            results.append({run.name: run})
        print(CmdLineOutputEncoder().encode(results))

    else:  # plaintext, csv
        header = ['Name', 'Number of unresolved reports',
                  'Analyzer statistics', 'Storage date', 'Version tag',
                  'Duration', 'CodeChecker version']
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

            rows.append((run.name,
                         str(run.resultCount),
                         ', '.join(analyzer_statistics),
                         run.runDate,
                         run.versionTag if run.versionTag else '',
                         duration,
                         codechecker_version))

        print(twodim_to_str(args.output_format, header, rows))


def handle_list_results(args):
    init_logger(args.verbose if 'verbose' in args else None)
    check_deprecated_arg_usage(args)

    client = setup_client(args.product_url)

    run_names = map(lambda x: x.strip(), args.name.split(':'))
    run_ids = [run.runId for run in get_runs(client, run_names)]

    if not len(run_ids):
        LOG.warning("No runs were found!")
        sys.exit(1)

    limit = constants.MAX_QUERY_SIZE
    offset = 0

    report_filter = ttypes.ReportFilter()

    add_filter_conditions(client, report_filter, args)

    all_results = []
    results = client.getRunResults(run_ids, limit, offset, None,
                                   report_filter, None)

    while results:
        all_results.extend(results)
        offset += limit
        results = client.getRunResults(run_ids, limit, offset, None,
                                       report_filter, None)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(all_results))
    else:
        header = ['File', 'Checker', 'Severity', 'Msg', 'Review status',
                  'Detection status']

        rows = []
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

            rows.append((checked_file, res.checkerId, sev,
                         res.checkerMsg, rw_status, dt_status))

        print(twodim_to_str(args.output_format, header, rows))


def handle_diff_results(args):

    init_logger(args.verbose if 'verbose' in args else None)
    check_deprecated_arg_usage(args)

    f_severities, f_checkers, f_file_path, _, _ = check_filter_values(args)

    context = package_context.get_context()

    def skip_report_dir_result(report):
        """
        Returns True if the report should be skipped from the results based on
        the given filter set.
        """
        if f_severities:
            severity_name = context.severity_map.get(report.main['check_name'])
            if severity_name.lower() not in map(str.lower, f_severities):
                return True

        if f_checkers:
            checker_name = report.main['check_name']
            if not any([re.match(r'^' + c.replace("*", ".*") + '$',
                                 checker_name, re.IGNORECASE)
                        for c in f_checkers]):
                return True

        if f_file_path:
            file_path = report.files[int(report.main['location']['file'])]
            if not any([re.match(r'^' + f.replace("*", ".*") + '$',
                                 file_path, re.IGNORECASE)
                        for f in f_file_path]):
                return True

        if 'checker_msg' in args:
            checker_msg = report.main['description']
            if not any([re.match(r'^' + c.replace("*", ".*") + '$',
                                 checker_msg, re.IGNORECASE)
                        for c in args.checker_msg]):
                return True

        return False

    def get_report_dir_results(reportdir):
        all_reports = []
        processed_path_hashes = set()
        for filename in os.listdir(reportdir):
            if filename.endswith(".plist"):
                file_path = os.path.join(reportdir, filename)
                LOG.debug("Parsing: %s", file_path)
                try:
                    files, reports = plist_parser.parse_plist(file_path)
                    for report in reports:
                        path_hash = get_report_path_hash(report, files)
                        if path_hash in processed_path_hashes:
                            LOG.debug("Not showing report because it is a "
                                      "deduplication of an already processed "
                                      "report!")
                            LOG.debug("Path hash: %s", path_hash)
                            LOG.debug(report)
                            continue

                        if skip_report_dir_result(report):
                            continue

                        processed_path_hashes.add(path_hash)
                        report.main['location']['file_name'] = \
                            files[int(report.main['location']['file'])]
                        all_reports.append(report)

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
        add_filter_conditions(client, report_filter, args)

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

    def get_suppressed_reports(reports):
        """
        Returns suppressed reports.
        """
        suppressed_in_code = []
        for rep in reports:
            bughash = rep.report_hash
            source_file = rep.main['location']['file_name']
            bug_line = rep.main['location']['line']
            checker_name = rep.main['check_name']

            sc_handler = SourceCodeCommentHandler(source_file)
            src_comment_data = sc_handler.filter_source_line_comments(
                bug_line,
                checker_name)

            if len(src_comment_data) == 1:
                suppressed_in_code.append(bughash)
                LOG.debug("Bug %s is suppressed in code. file: %s Line %s",
                          bughash, source_file, bug_line)
            elif len(src_comment_data) > 1:
                LOG.warning(
                    "Multiple source code comment can be found "
                    "for '%s' checker in '%s' at line %s. "
                    "This bug will not be suppressed!",
                    checker_name, source_file, bug_line)
        return suppressed_in_code

    def get_diff_type():
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

    def get_diff_local_dir_remote_run(client, report_dir, run_name):
        """
        Compares a local report directory with a remote run.
        """
        filtered_reports = []
        report_dir_results = get_report_dir_results(
            os.path.abspath(report_dir))
        suppressed_in_code = get_suppressed_reports(report_dir_results)

        diff_type = get_diff_type()
        run_ids, run_names, _ = process_run_arg(run_name)
        local_report_hashes = set([r.report_hash for r in report_dir_results])

        if diff_type == ttypes.DiffType.NEW:
            # Get report hashes which can be found only in the remote runs.
            remote_hashes = \
                client.getDiffResultsHash(run_ids,
                                          local_report_hashes,
                                          ttypes.DiffType.RESOLVED)

            results = get_diff_base_results(client, run_ids,
                                            remote_hashes,
                                            suppressed_in_code)
            for result in results:
                filtered_reports.append(result)
        elif diff_type == ttypes.DiffType.UNRESOLVED:
            # Get remote hashes which can be found in the remote run and in the
            # local report directory.
            remote_hashes = \
                client.getDiffResultsHash(run_ids,
                                          local_report_hashes,
                                          ttypes.DiffType.UNRESOLVED)
            for result in report_dir_results:
                rep_h = result.report_hash
                if rep_h in remote_hashes and rep_h not in suppressed_in_code:
                    filtered_reports.append(result)
        elif diff_type == ttypes.DiffType.RESOLVED:
            # Get remote hashes which can be found in the remote run and in the
            # local report directory.
            remote_hashes = \
                client.getDiffResultsHash(run_ids,
                                          local_report_hashes,
                                          ttypes.DiffType.UNRESOLVED)
            for result in report_dir_results:
                if result.report_hash not in remote_hashes:
                    filtered_reports.append(result)

        return filtered_reports, run_names

    def get_diff_remote_run_local_dir(client, run_name, report_dir):
        """
        Compares a remote run with a local report directory.
        """
        filtered_reports = []
        report_dir_results = get_report_dir_results(
            os.path.abspath(report_dir))
        suppressed_in_code = get_suppressed_reports(report_dir_results)

        diff_type = get_diff_type()
        run_ids, run_names, _ = process_run_arg(run_name)
        local_report_hashes = set([r.report_hash for r in report_dir_results])

        remote_hashes = client.getDiffResultsHash(run_ids,
                                                  local_report_hashes,
                                                  diff_type)

        if diff_type in [ttypes.DiffType.NEW, ttypes.DiffType.UNRESOLVED]:
            # Shows reports from the report dir which are not present in
            # the baseline (NEW reports) or appear in both side (UNRESOLVED
            # reports) and not suppressed in the code.
            for result in report_dir_results:
                rep_h = result.report_hash
                if rep_h in remote_hashes and rep_h not in suppressed_in_code:
                    filtered_reports.append(result)
        elif diff_type == ttypes.DiffType.RESOLVED:
            # Show bugs in the baseline (server) which are not present in
            # the report dir or suppressed.
            results = get_diff_base_results(client,
                                            run_ids,
                                            remote_hashes,
                                            suppressed_in_code)
            for result in results:
                filtered_reports.append(result)

        return filtered_reports, run_names

    def get_diff_remote_runs(client, basename, newname):
        """
        Compares two remote runs and returns the filtered results.
        """
        report_filter = ttypes.ReportFilter()
        add_filter_conditions(client, report_filter, args)

        base_ids, base_run_names, base_run_tags = process_run_arg(basename)
        report_filter.runTag = base_run_tags

        cmp_data = ttypes.CompareData()
        cmp_data.diffType = get_diff_type()

        new_ids, new_run_names, new_run_tags = process_run_arg(newname)
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
        limit = constants.MAX_QUERY_SIZE
        offset = 0

        all_results = []
        results = client.getRunResults(base_ids,
                                       limit,
                                       offset,
                                       sort_mode,
                                       report_filter,
                                       cmp_data)

        while results:
            all_results.extend(results)
            offset += limit
            results = client.getRunResults(base_ids,
                                           limit,
                                           offset,
                                           sort_mode,
                                           report_filter,
                                           cmp_data)
        return all_results, base_run_names, new_run_names

    def get_diff_local_dirs(basename, newname):
        """
        Compares two report directories and returns the filtered results.
        """
        filtered_reports = []
        base_results = get_report_dir_results(os.path.abspath(basename))
        new_results = get_report_dir_results(os.path.abspath(newname))

        base_hashes = set([res.report_hash for res in base_results])
        new_hashes = set([res.report_hash for res in new_results])

        diff_type = get_diff_type()
        if diff_type == ttypes.DiffType.NEW:
            for res in new_results:
                if res.report_hash not in base_hashes:
                    filtered_reports.append(res)
        if diff_type == ttypes.DiffType.UNRESOLVED:
            for res in new_results:
                if res.report_hash in base_hashes:
                    filtered_reports.append(res)
        elif diff_type == ttypes.DiffType.RESOLVED:
            for res in base_results:
                if res.report_hash not in new_hashes:
                    filtered_reports.append(res)

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

    def reports_to_report_data(reports):
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
            for file_index, file_path in enumerate(report.files):
                if file_index not in file_sources:
                    try:
                        with io.open(file_path, 'r', encoding='UTF-8',
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
                'path': report.main['location']['file_name'],
                'reportHash': report_hash,
                'checkerName': report.main['check_name']})

        return {'files': file_sources,
                'reports': report_data}

    def report_to_html(client, reports, output_dir):
        """
        Generate HTML output files for the given reports in the given output
        directory by using the Plist To HTML parser.
        """
        html_builder = PlistToHtml.HtmlBuilder(
            context.path_plist_to_html_dist,
            context.severity_map)

        file_report_map = defaultdict(list)
        for report in reports:
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

        html_builder.create_index_html(output_dir)

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
                  '  $ firefox {0}'.format(os.path.join(args.export_dir,
                                                        'index.html')))
            return

        header = ['File', 'Checker', 'Severity', 'Msg', 'Source']
        rows = []

        source_lines = defaultdict(set)
        for report in reports:
            if not isinstance(report, Report) and report.line is not None:
                source_lines[report.fileId].add(report.line)

        lines_in_files_requested = []
        for key in source_lines:
            lines_in_files_requested.append(
                ttypes.LinesInFilesRequested(fileId=key,
                                             lines=source_lines[key]))

        for report in reports:
            source_line = ''
            if isinstance(report, Report):
                # report is coming from a plist file.
                bug_line = report.main['location']['line']
                bug_col = report.main['location']['col']
                checked_file = report.main['location']['file_name']\
                    + ':' + str(bug_line) + ":" + str(bug_col)
                check_name = report.main['check_name']
                sev = context.severity_map.get(check_name)
                check_msg = report.main['description']
                source_line =\
                    get_line_from_file(report.main['location']['file_name'],
                                       bug_line)
            else:
                # report is of ReportData type coming from CodeChecker server.
                bug_line = report.line
                bug_col = report.column
                sev = ttypes.Severity._VALUES_TO_NAMES[report.severity]
                checked_file = report.checkedFile
                if bug_line is not None:
                    checked_file += ':' + str(bug_line) + ":" + str(bug_col)

                check_name = report.checkerId
                check_msg = report.checkerMsg

                if lines_in_files_requested:
                    source_line_contents = client.getLinesInSourceFileContents(
                        lines_in_files_requested, ttypes.Encoding.BASE64)
                    source_line = base64.b64decode(
                        source_line_contents[report.fileId][bug_line])
            rows.append(
                (sev, checked_file, check_msg, check_name, source_line))
        if output_format == 'plaintext':
            for row in rows:
                print("[{0}] {1}: {2} [{3}]\n{4}\n".format(
                    row[0], row[1], row[2], row[3], row[4]))
        else:
            print(twodim_to_str(output_format, header, rows))

    def get_run_tag(client, run_ids, tag_name):
        """
        Returns run tag information for the given tag name in the given runs.
        """
        run_history_filter = ttypes.RunHistoryFilter()
        run_history_filter.tagNames = [tag_name]
        run_histories = client.getRunHistory(run_ids, None, None,
                                             run_history_filter)

        return run_histories[0] if len(run_histories) else None

    def process_run_arg(run_arg_with_tag):
        """
        Process the argument and returns run ids a run tag ids.
        The argument has the following format: <run_name>:<run_tag>
        """
        run_with_tag = run_arg_with_tag.split(':')
        run_name = run_with_tag[0]

        runs = get_runs(client, [run_name])
        run_ids = map(lambda run: run.runId, runs)
        run_names = map(lambda run: run.name, runs)

        # Set base run tag if it is available.
        run_tag_name = run_with_tag[1] if len(run_with_tag) > 1 else None
        run_tags = None
        if run_tag_name:
            tag = get_run_tag(client, run_ids, run_tag_name)
            run_tags = [tag.id] if tag else None

        if not run_ids:
            LOG.warning(
                "No run names match the given pattern: %s", run_arg_with_tag)
            sys.exit(1)

        LOG.info("Matching runs: %s",
                 ', '.join(map(lambda run: run.name, runs)))

        return run_ids, run_names, run_tags

    def print_diff_results(reports):
        """
        Print the results.
        """
        if reports:
            print_reports(client, reports, args.output_format)
        else:
            LOG.info("No results.")

    client = None

    # We set up the client if we are not comparing two local report directory.
    if not os.path.isdir(args.basename) or not os.path.isdir(args.newname):
        client = setup_client(args.product_url)

    if os.path.isdir(args.basename) and os.path.isdir(args.newname):
        reports = get_diff_local_dirs(args.basename, args.newname)
        print_diff_results(reports)
        LOG.info("Compared two local report directories %s and %s",
                 os.path.abspath(args.basename),
                 os.path.abspath(args.newname))
    elif os.path.isdir(args.newname):
        reports, base_run_names = \
            get_diff_remote_run_local_dir(client,
                                          args.basename,
                                          os.path.abspath(args.newname))
        print_diff_results(reports)
        LOG.info("Compared remote run(s) %s (matching: %s) and local report "
                 "directory %s",
                 args.basename,
                 ', '.join(base_run_names),
                 os.path.abspath(args.newname))
    elif os.path.isdir(args.basename):
        reports, new_run_names = \
            get_diff_local_dir_remote_run(client,
                                          os.path.abspath(args.basename),
                                          args.newname)
        print_diff_results(reports)
        LOG.info("Compared local report directory %s and remote run(s) %s "
                 "(matching: %s).",
                 os.path.abspath(args.basename),
                 args.newname,
                 ', '.join(new_run_names))
    else:
        reports, base_run_names, new_run_names = \
            get_diff_remote_runs(client, args.basename, args.newname)
        print_diff_results(reports)
        LOG.info("Compared multiple remote runs %s (matching: %s) and %s "
                 "(matching: %s)",
                 args.basename,
                 ', '.join(base_run_names),
                 args.newname,
                 ', '.join(new_run_names))


def handle_list_result_types(args):

    init_logger(args.verbose if 'verbose' in args else None)
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
        run_ids = [run.runId for run in get_runs(client, args.names)]
        if not len(run_ids):
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

    resolved_checkers = get_statistics(client, run_ids, 'detectionStatus',
                                       [ttypes.DetectionStatus.RESOLVED])

    # Get severity counts
    report_filter = ttypes.ReportFilter()
    add_filter_conditions(client, report_filter, args)

    sev_count = client.getSeverityCounts(run_ids, report_filter, None)
    severities = []
    severity_total = 0
    for key, count in sorted(sev_count.items(),
                             reverse=True):
        severities.append(dict(
            severity=ttypes.Severity._VALUES_TO_NAMES[key],
            reports=count))
        severity_total += count

    all_results = []
    total = defaultdict(int)
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
        total['total_reports'] += checker_data.count
        total['total_resolved'] += checker_count(resolved_checkers, key)
        total['total_unreviewed'] += checker_count(unrev_checkers, key)
        total['total_confirmed'] += checker_count(confirmed_checkers, key)
        total['total_false_positive'] += checker_count(false_checkers, key)
        total['total_intentional'] += checker_count(intentional_checkers, key)

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

        rows.append(('Total', '-', str(total['total_reports']),
                     str(total['total_resolved']),
                     str(total['total_unreviewed']),
                     str(total['total_confirmed']),
                     str(total['total_false_positive']),
                     str(total['total_intentional'])))

        print(twodim_to_str(args.output_format, header, rows,
                            separate_footer=True))

        # Print severity counts
        header = ['Severity', 'All reports']

        rows = []
        for stat in severities:
            rows.append((stat['severity'],
                         str(stat['reports'])))

        rows.append(('Total', str(severity_total)))

        print(twodim_to_str(args.output_format, header, rows,
                            separate_footer=True))


def handle_remove_run_results(args):

    init_logger(args.verbose if 'verbose' in args else None)

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

    for run_id in [run.runId for run in client.getRunData(None)
                   if condition(run.name, run.runId, run.runDate)]:
        client.removeRun(run_id)

    LOG.info("Done.")


def handle_suppress(args):

    init_logger(args.verbose if 'verbose' in args else None)

    limit = constants.MAX_QUERY_SIZE

    client = setup_client(args.product_url)

    run_info = check_run_names(client, [args.name])
    run = run_info.get(args.name)

    if 'input' in args:
        with open(args.input) as supp_file:
            suppress_data = suppress_file_handler.get_suppress_data(supp_file)

        for bug_id, file_name, comment, status in suppress_data:
            file_name = '%' + file_name
            bug_hash_filter = ttypes.ReportFilter(filepath=[file_name],
                                                  reportHash=[bug_id])
            reports = client.getRunResults([run.runId], limit, 0, None,
                                           bug_hash_filter,
                                           None)

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
    handle_auth(protocol, host, port, args.username,
                login='logout' not in args)


def handle_list_run_histories(args):
    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)
    run_ids = None
    if 'names' in args:
        runs = get_runs(client, args.names)
        run_ids = [r.runId for r in runs]

    run_history = client.getRunHistory(run_ids, None, None, None)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(run_history))
    else:  # plaintext, csv
        header = ['Date', 'Run name', 'Version tag', 'User',
                  'CodeChecker version', 'Analyzer statistics']
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
                         ', '.join(analyzer_statistics)))

        print(twodim_to_str(args.output_format, header, rows))
