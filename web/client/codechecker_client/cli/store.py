# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
'CodeChecker store' parses a list of analysis results and stores them in the
database.
"""


import argparse
import base64
import functools
import hashlib
import json
import os
import signal
import sys
import tempfile
import uuid
import zipfile
import zlib
import shutil

from collections import defaultdict, namedtuple
from contextlib import contextmanager
from datetime import timedelta
from threading import Timer
from typing import Dict, Iterable, List, Set, Tuple

from codechecker_api.codeCheckerDBAccess_v6.ttypes import \
    StoreLimitKind, SubmittedRunOptions

from codechecker_report_converter import twodim
from codechecker_report_converter.report import Report, report_file, \
    reports as reports_helper, statistics as report_statistics
from codechecker_report_converter.report.hash import HashType, \
    get_report_path_hash
from codechecker_report_converter.report.parser.base import AnalyzerInfo

try:
    from codechecker_client.blame_info import assemble_blame_info
except ImportError:
    def assemble_blame_info(_, __) -> int:
        """
        Shim for cases where Git blame info is not gatherable due to
        missing libraries.
        """
        raise NotImplementedError()

from codechecker_client import client as libclient, product
from codechecker_client.task_client import await_task_termination
from codechecker_common import arg, logger, cmd_config
from codechecker_common.checker_labels import CheckerLabels
from codechecker_common.compatibility.multiprocessing import Pool
from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler
from codechecker_common.util import format_size, load_json, strtobool

from codechecker_web.shared import webserver_context, host_check
from codechecker_web.shared.env import get_default_workspace


LOG = logger.get_logger('system')

MAX_UPLOAD_SIZE = 1024 ** 3  # 1024^3 = 1 GiB.


AnalyzerResultFileReports = Dict[str, List[Report]]


FileReportPositions = Dict[str, Set[int]]


"""Minimal required information for a report position in a source file.

line: line number where the report was generated
fileidx: is the file index in the generated plist report file
filepath: the absolute path to the souce file
"""
ReportLineInfo = namedtuple('ReportLineInfo',
                            ['line', 'fileidx', 'filepath'])


"""Contains information about the report file after parsing.

store_it: True if every information is available and the
            report can be stored
main_report_positions: list of ReportLineInfo containing
                        the main report positions
"""
ReportFileInfo = namedtuple('ReportFileInfo',
                            ['store_it', 'main_report_positions'])


"""Contains information about the source files mentioned in a report file.

source_info: a dictionary about all the mentioned source files
             the key is the source file, the value is content hash and last
             modification time if the file exists if not the value is empty
missing: a set of the missing source files (absoute path)
changed_since_report_gen: set of source files where the last modification
                        timestamp is newer then the report file which
                        mentiones it.
"""
SourceFilesInReport = namedtuple('SourceFilesInReport',
                                 ['source_info', 'missing',
                                  'changed_since_report_gen'])


class StorageZipStatistics(report_statistics.Statistics):
    def __init__(self):
        super().__init__()

        self.num_of_blame_information = 0
        self.num_of_source_files = 0
        self.num_of_source_files_with_source_code_comment = 0

    def _write_summary(self, out=sys.stdout):
        """ Print summary. """
        out.write("\n----======== Summary ========----\n")
        statistics_rows = [
            ["Number of processed analyzer result files",
             str(self.num_of_analyzer_result_files)],
            ["Number of analyzer reports", str(self.num_of_reports)],
            ["Number of source files", str(self.num_of_source_files)],
            ["Number of source files with source code comments",
             str(self.num_of_source_files_with_source_code_comment)],
            ["Number of blame information files",
             str(self.num_of_blame_information)]]
        out.write(twodim.to_table(statistics_rows, False))
        out.write("\n----=================----\n")


def get_file_content_hash(file_path):
    """
    Return the file content hash for a file.
    """
    with open(file_path, 'rb') as content:
        hasher = hashlib.sha256()
        hasher.update(content.read())
        return hasher.hexdigest()


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker store',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': """
Store the results from one or more 'codechecker-analyze' result files in a
database.""",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': """
Environment variables
------------------------------------------------
  CC_PASS_FILE     The location of the password file for auto login. By default
                   CodeChecker will use '~/.codechecker.passwords.json' file.
                   It can also be used to setup different credential files to
                   login to the same server with a different user.

  CC_SESSION_FILE  The location of the session file where valid sessions are
                   stored. This file will be automatically created by
                   CodeChecker. By default CodeChecker will use
                   '~/.codechecker.session.json'. This can be used if
                   restrictive permissions forbid CodeChecker from creating
                   files in the users home directory (e.g. in a CI
                   environment).


The results can be viewed by connecting to such a server in a Web browser or
via 'CodeChecker cmd'.""",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Save analysis results to a database."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('input',
                        type=str,
                        nargs='*',
                        metavar='file/folder',
                        default=os.path.join(get_default_workspace(),
                                             'reports'),
                        help="The analysis result files and/or folders "
                             "containing analysis results which should be "
                             "parsed and printed. If multiple report "
                             "directories are given, OFF and UNAVAILABLE "
                             "detection statuses will not be available.")

    parser.add_argument('-t', '--type', '--input-format',
                        dest="input_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results were "
                             "created as.")

    parser.add_argument('-n', '--name',
                        type=str,
                        dest="name",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The name of the analysis run to use in storing "
                             "the reports to the database. If not specified, "
                             "the '--name' parameter given to 'codechecker-"
                             "analyze' will be used, if exists.")

    parser.add_argument('--tag',
                        type=str,
                        dest="tag",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="A uniques identifier for this individual store "
                             "of results in the run's history.")

    parser.add_argument('--description',
                        type=str,
                        dest="description",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="A custom textual description to be shown "
                             "alongside the run.")

    parser.add_argument('--trim-path-prefix',
                        type=str,
                        nargs='*',
                        dest="trim_path_prefix",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Removes leading path from files which will be "
                             "printed. For instance if you analyze files "
                             "'/home/jsmith/my_proj/x.cpp' and "
                             "'/home/jsmith/my_proj/y.cpp', but would prefer "
                             "to have them displayed as 'my_proj/x.cpp' and "
                             "'my_proj/y.cpp' in the web/CLI interface, "
                             "invoke CodeChecker with '--trim-path-prefix "
                             "\"/home/jsmith/\"'."
                             "If multiple prefixes are given, the longest "
                             "match will be removed. You may also use Unix "
                             "shell-like wildcards (e.g. '/*/jsmith/').")

    parser.add_argument('--temp_dir',
                        type=str,
                        metavar='PATH',
                        required=False,
                        default=None,
                        dest="temp_dir",
                        help="Specify the location to write the compressed "
                        "file used for storage. Useful if the results "
                        "directory is read only. "
                        "Defaults to the results directory.")

    parser.add_argument("--detach",
                        dest="detach",
                        default=argparse.SUPPRESS,
                        action="store_true",
                        required=False,
                        help="""
Runs `store` in fire-and-forget mode: exit immediately once the server accepted
the analysis reports for storing, without waiting for the server-side data
processing to conclude.
Doing this is generally not recommended, as the client will never be notified
of potential processing failures, and there is no easy way to wait for the
successfully stored results to become available server-side for potential
further processing (e.g., `CodeChecker cmd diff`).
However, using '--detach' can significantly speed up large-scale monitoring
analyses where access to the results by a tool is not a goal, such as in the
case of non-gating CI systems.
""")

    cmd_config.add_option(parser)

    parser.add_argument('-f', '--force',
                        dest="force",
                        default=argparse.SUPPRESS,
                        action='store_true',
                        required=False,
                        help="Delete analysis results stored in the database "
                             "for the current analysis run's name and store "
                             "only the results reported in the 'input' files. "
                             "(By default, CodeChecker would keep reports "
                             "that were coming from files not affected by the "
                             "analysis, and only incrementally update defect "
                             "reports for source files that were analysed.)")

    server_args = parser.add_argument_group(
        "server arguments", """
Specifies a 'CodeChecker server' instance which will be used to store the
results. This server must be running and listening, and the given product must
exist prior to the 'store' command being ran.""")

    server_args.add_argument('--url',
                             type=str,
                             metavar='PRODUCT_URL',
                             dest="product_url",
                             default="localhost:8001/Default",
                             required=False,
                             help="The URL of the product to store the "
                                  "results for, in the format of "
                                  "'[http[s]://]host:port/Endpoint'.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(
        func=main, func_process_config_file=cmd_config.process_config_file)


def __get_run_name(input_list):
    """Create a runname for the stored analysis from the input list."""

    # Try to create a name from the metadata JSON(s).
    names = set()
    for input_path in input_list:
        metafile = os.path.join(input_path, "metadata.json")
        if os.path.isdir(input_path) and os.path.exists(metafile):
            metajson = load_json(metafile)

            if 'version' in metajson and metajson['version'] >= 2:
                for tool in metajson.get('tools', {}):
                    name = tool.get('run_name')
            else:
                name = metajson.get('name')

            if not name:
                name = "unnamed result folder"

            names.add(name)

    if len(names) == 1:
        name = names.pop()
        if name != "unnamed result folder":
            return name
    elif len(names) > 1:
        return "multiple projects: " + ', '.join(names)

    return False


def scan_for_review_comment(job: Tuple[str, Iterable[int]]):
    """Scan a file for review comments returns
    all the found review comments.
    """
    file_path, lines = job
    sc_handler = SourceCodeCommentHandler()
    comments = []
    with open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
        comments, misspelled_comments = sc_handler.scan_source_line_comments(
            f, lines)

        if misspelled_comments:
            LOG.warning("There are misspelled review status comments in %s",
                        file_path)
        for mc in misspelled_comments:
            LOG.warning(mc)

    return comments


def get_source_file_with_comments(jobs, zip_iter=map) -> Set[str]:
    """
    Get source files where there is any codechecker review comment at the main
    report positions.
    """
    files_with_comment = set()

    for job, comments in zip(jobs, zip_iter(scan_for_review_comment, jobs)):
        file_path, _ = job
        if comments:
            files_with_comment.add(file_path)

    return files_with_comment


def filter_source_files_with_comments(
    file_report_positions: FileReportPositions
) -> Set[str]:
    """ Collect the source files where there is any codechecker review
    comment at the main report positions.
    """
    jobs = file_report_positions.items()

    with Pool() as executor:
        return get_source_file_with_comments(jobs, executor.map)


def get_reports(
    analyzer_result_file_path: str,
    checker_labels: CheckerLabels
) -> List[Report]:
    """ Get reports from the given analyzer result file. """
    reports = report_file.get_reports(
        analyzer_result_file_path, checker_labels)

    # CppCheck generates a '0' value for the report hash. In case all of the
    # reports in a result file contain only a hash with '0' value, overwrite
    # the hash values in the report files with a context free hash value.
    if all(r.report_hash == '0' for r in reports):
        report_file.replace_report_hash(
            analyzer_result_file_path, HashType.CONTEXT_FREE)

        reports = report_file.get_reports(
            analyzer_result_file_path, checker_labels)

    return reports


def parse_analyzer_result_files(
    analyzer_result_files: Iterable[str],
    checker_labels: CheckerLabels,
    zip_iter=map
) -> AnalyzerResultFileReports:
    """ Get reports from the given analyzer result files. """
    analyzer_result_file_reports: AnalyzerResultFileReports = defaultdict(list)

    for idx, (file_path, reports) in enumerate(zip(
            analyzer_result_files, zip_iter(
                functools.partial(get_reports, checker_labels=checker_labels),
                analyzer_result_files))):
        LOG.debug(f"[{idx}/{len(analyzer_result_files)}] "
                  f"Parsed '{file_path}' ...")
        analyzer_result_file_reports[file_path] = reports

    return analyzer_result_file_reports


class ReportLimitExceedError(Exception):
    """
    Custom exception type thrown by 'assemble_zip'. This is used when the
    unique reports count is greater then the set limit in the product config.
    """
    def __init__(self, message):
        super().__init__(self, message)


def assemble_zip(inputs,
                 zip_file,
                 client,
                 prod_client,
                 checker_labels: CheckerLabels,
                 tmp_dir: str):
    """Collect and compress report and source files, together with files
    contanining analysis related information into a zip file which
    will be sent to the server.

    For each report directory, we create a uniqued zipped directory. Each
    report directory to store could have been made with different
    configurations, so we can't merge them all into a single zip.
    """
    files_to_compress: Dict[str, set] = defaultdict(set)
    analyzer_result_file_paths = []
    stats = StorageZipStatistics()

    for dir_path, file_paths in report_file.analyzer_result_files(inputs):
        analyzer_result_file_paths.extend(file_paths)

        metadata_file_path = os.path.join(dir_path, 'metadata.json')
        if os.path.exists(metadata_file_path):
            files_to_compress[os.path.dirname(metadata_file_path)] \
                .add(metadata_file_path)

        skip_file_path = os.path.join(dir_path, 'skip_file')
        if os.path.exists(skip_file_path):
            with open(skip_file_path, 'r', encoding='utf-8') as f:
                LOG.info("Found skip file %s with the following content:\n%s",
                         skip_file_path, f.read())

            files_to_compress[os.path.dirname(skip_file_path)] \
                .add(skip_file_path)

        review_status_file_path = os.path.join(dir_path, 'review_status.yaml')
        if os.path.exists(review_status_file_path):
            files_to_compress[os.path.dirname(review_status_file_path)]\
                .add(review_status_file_path)

    LOG.debug(f"Processing {len(analyzer_result_file_paths)} report files ...")

    with Pool() as executor:
        analyzer_result_file_reports = parse_analyzer_result_files(
             analyzer_result_file_paths, checker_labels, executor.map)

    LOG.info("Processing report files done.")

    changed_files = set()
    file_paths = set()
    file_report_positions: FileReportPositions = defaultdict(set)
    unique_reports: Dict[str, Dict[str, List[Report]]] = defaultdict(dict)

    unique_report_hashes = set()
    for file_path, reports in analyzer_result_file_reports.items():
        stats.num_of_analyzer_result_files += 1

        for report in reports:
            if report.changed_files:
                changed_files.update(report.changed_files)
                continue
            # Unique all bug reports per report directory; also, count how many
            # reports we want to store at once to check for the report store
            # limit.
            report_path_hash = get_report_path_hash(report)
            if report_path_hash not in unique_report_hashes:
                unique_report_hashes.add(report_path_hash)
                unique_reports[os.path.dirname(file_path)]\
                    .setdefault(report.analyzer_name, []) \
                    .append(report)
                stats.add_report(report)

            file_paths.update(report.original_files)
            file_report_positions[report.file.original_path].add(report.line)

    temp_dir = tempfile.mkdtemp('-unique-plists', dir=tmp_dir)
    for dirname, analyzer_reports in unique_reports.items():
        for analyzer_name, reports in analyzer_reports.items():
            if not analyzer_name:
                analyzer_name = 'unknown'
            tmpfile = os.path.join(
                temp_dir, f'{uuid.uuid4()}-{analyzer_name}.plist')

            report_file.create(tmpfile, reports, checker_labels,
                               AnalyzerInfo(analyzer_name))
            LOG.debug(f"Stored '{analyzer_name}' unique reports in {tmpfile}.")
            files_to_compress[dirname].add(tmpfile)

    if changed_files:
        reports_helper.dump_changed_files(changed_files)
        shutil.rmtree(temp_dir)
        sys.exit(1)

    if not file_paths:
        LOG.warning("There is no report to store. After uploading these "
                    "results the previous reports become resolved.")

    hash_to_file: Dict[str, str] = {}

    # There can be files with same hash, but different path.
    file_to_hash: Dict[str, str] = {}

    for file_path in file_paths:
        h = get_file_content_hash(file_path)

        file_to_hash[file_path] = h
        hash_to_file[h] = file_path

    file_hashes = list(hash_to_file.keys())

    LOG.info("Get missing file content hashes from the server...")
    necessary_hashes = client.getMissingContentHashes(file_hashes) \
        if file_hashes else []
    LOG.info("Get missing file content hashes done.")

    LOG.info(
        "Get file content hashes which do not have blame information from the "
        "server...")
    necessary_blame_hashes = \
        client.getMissingContentHashesForBlameInfo(file_hashes) \
        if file_hashes else []
    LOG.info(
        "Get file content hashes which do not have blame information done.")

    LOG.info("Collecting review comments ...")

    # Get files which can be found on the server but contains source code
    # comments and send these files to the server.
    unnecessary_file_report_positions = {
        k: v for (k, v) in file_report_positions.items()
        if file_to_hash[k] not in necessary_hashes}

    files_with_comment = filter_source_files_with_comments(
        unnecessary_file_report_positions)

    for file_path in files_with_comment:
        necessary_hashes.append(file_to_hash[file_path])
        stats.num_of_source_files_with_source_code_comment += 1

    LOG.info("Collecting review comments done.")

    LOG.info("Building report zip file...")
    with zipfile.ZipFile(zip_file, 'a', allowZip64=True) as zipf:
        # Add the files to the zip which will be sent to the server.

        for dirname, files in files_to_compress.items():
            for file_path in files:
                _, file_name = os.path.split(file_path)

                # Create a unique report directory name.
                report_dir_name = \
                    hashlib.md5(dirname.encode('utf-8')).hexdigest()
                zip_target = \
                    os.path.join('reports', report_dir_name, file_name)
                zipf.write(file_path, zip_target)

        collected_file_paths = set()
        for f, h in file_to_hash.items():
            if h in necessary_hashes:
                LOG.debug("File contents for '%s' needed by the server", f)

                file_path = os.path.join('root', f.lstrip('/'))
                collected_file_paths.add(f)
                stats.num_of_source_files += 1
                try:
                    zipf.getinfo(file_path)
                except KeyError:
                    zipf.write(f, file_path)

        if necessary_blame_hashes:
            file_paths = list(f for f, h in file_to_hash.items()
                              if h in necessary_blame_hashes)

            LOG.info("Collecting blame information for source files...")
            try:
                stats.num_of_blame_information = assemble_blame_info(
                    zipf, file_paths)

                if stats.num_of_blame_information:
                    LOG.info("Collecting blame information... Done.")
                else:
                    LOG.info("No blame information found for source files.")
            except NotImplementedError:
                LOG.warning(
                    "Failed to collect blame information. Make sure Git is "
                    "installed on your system.")

        zipf.writestr('content_hashes.json', json.dumps(file_to_hash))

    LOG.info("Building report zip file (%s) done.", zip_file)

    # Print statistics what will be stored to the server.
    stats.write()

    # Fail store early if too many reports.
    p = prod_client.getCurrentProduct()
    if len(unique_report_hashes) > p.reportLimit:
        LOG.error(f"""Report Limit Exceeded

This report folder cannot be stored because the number of reports in the
result folder is too high. Usually noisy checkers, generating a lot of
reports are not useful and it is better to disable them.

Run `CodeChecker parse <report_folder>` to gain a better understanding on
report counts.

Disable checkers that have generated an excessive number of reports and then
rerun the analysis to be able to store the results on the server.

Configured report limit for this product: {p.reportLimit}
        """)
        shutil.rmtree(temp_dir)
        raise ReportLimitExceedError("Maximum report limit reached.")

    zip_size = os.stat(zip_file).st_size

    LOG.info("Compressing report zip file...")

    with open(zip_file, 'rb') as source:
        compressed = zlib.compress(source.read(), zlib.Z_BEST_COMPRESSION)
    with open(zip_file, 'wb') as target:
        target.write(compressed)

    compressed_zip_size = os.stat(zip_file).st_size

    LOG.info("Compressing report zip file done (%s / %s).",
             format_size(zip_size), format_size(compressed_zip_size))

    # We are responsible for deleting these.
    shutil.rmtree(temp_dir)


def should_be_zipped(input_file: str, input_files: Iterable[str]) -> bool:
    """
    Determine whether a given input file should be included in the zip.
    Compiler includes and target files should only be included if there is
    no compiler info file present.
    """
    return (input_file in ['metadata.json', 'compiler_info.json']
            or (input_file in ['compiler_includes.json',
                               'compiler_target.json']
                and 'compiler_info.json' not in input_files))


def get_analysis_statistics(inputs, limits):
    """
    Collects analysis statistics information and returns them.

    This function will return the path of failed zips and the following files:
      - compile_cmd.json
      - either
        - compiler_info.json, or
        - compiler_includes.json and compiler_target.json
      - metadata.json

    If the input directory doesn't contain any failed zip this function will
    return and empty list.
    """
    statistics_files = []
    has_failed_zip = False
    for input_path in inputs:
        dirs = []
        if os.path.isfile(input_path):
            files = [input_path]
        else:
            _, dirs, files = next(os.walk(input_path), ([], [], []))

        for inp_f in files:
            if inp_f == 'compile_cmd.json':
                compilation_db = os.path.join(input_path, inp_f)
                compilation_db_size = \
                    limits.get(StoreLimitKind.COMPILATION_DATABASE_SIZE)

                if os.stat(compilation_db).st_size > compilation_db_size:
                    LOG.debug("Compilation database is too big (max: %s).",
                              format_size(compilation_db_size))
                else:
                    LOG.debug("Copying file '%s' to analyzer statistics "
                              "ZIP...", compilation_db)
                    statistics_files.append(compilation_db)
            elif should_be_zipped(inp_f, files):
                analyzer_file = os.path.join(input_path, inp_f)
                statistics_files.append(analyzer_file)
        for inp_dir in dirs:
            if inp_dir == 'failed':
                failure_zip_limit = limits.get(StoreLimitKind.FAILURE_ZIP_SIZE)

                failed_dir = os.path.join(input_path, inp_dir)
                _, _, files = next(os.walk(failed_dir), ([], [], []))
                failed_files_size = 0
                for f in files:
                    failure_zip = os.path.join(failed_dir, f)
                    failure_zip_size = os.stat(failure_zip).st_size
                    failed_files_size += failure_zip_size

                    if failed_files_size > failure_zip_limit:
                        LOG.debug("We reached the limit of maximum uploadable "
                                  "failure zip size (max: %s).",
                                  format_size(failure_zip_limit))
                        break
                    else:
                        LOG.debug("Copying failure zip file '%s' to analyzer "
                                  "statistics ZIP...", failure_zip)
                        statistics_files.append(failure_zip)
                        has_failed_zip = True

        return statistics_files if has_failed_zip else []


def store_analysis_statistics(client, inputs, run_name):
    """
    Collects and stores analysis statistics information on the server.
    """
    zip_file_handle, zip_file = tempfile.mkstemp('.zip')
    LOG.debug("Will write failed store ZIP to '%s'...", zip_file)
    try:
        limits = client.getAnalysisStatisticsLimits()

        statistics_files = get_analysis_statistics(inputs, limits)

        if not statistics_files:
            LOG.debug("No analyzer statistics information can be found in the "
                      "report directory.")
            return None

        # Write statistics files to the ZIP file.
        with zipfile.ZipFile(zip_file, 'a', allowZip64=True) as zipf:
            for stat_file in statistics_files:
                zipf.write(stat_file)

        # Compressing .zip file
        with open(zip_file, 'rb') as source:
            compressed = zlib.compress(source.read(),
                                       zlib.Z_BEST_COMPRESSION)

        with open(zip_file, 'wb') as target:
            target.write(compressed)

        LOG.debug("[ZIP] Analysis statistics zip written at '%s'", zip_file)

        with open(zip_file, 'rb') as zf:
            b64zip = base64.b64encode(zf.read()).decode('utf-8')

        # Store analysis statistics on the server
        return client.storeAnalysisStatistics(run_name, b64zip)

    except Exception as ex:
        LOG.debug("Storage of analysis statistics zip has been failed: %s", ex)

    finally:
        os.close(zip_file_handle)
        os.remove(zip_file)

    return None


class WatchdogError(Exception):
    """
    Custom exception type thrown by '_timeout_watchdog'. This is used instead
    of the built-in 'TimeoutError' because TimeoutError <: OSError and other
    handlers in the call chain during a timeout might catch the more generic
    OSError instead, resulting in not running the appropriate handler.
    """
    def __init__(self, timeout: timedelta, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout


@contextmanager
def _timeout_watchdog(timeout: timedelta, trap: int):
    """
    Sets up a context with a 'threading.Timer' which will signal 'trap' the
    current process if 'timeout' passes. If and only if this 'trap' signal
    arrives, a 'WatchdogError' is thrown for appropriate handling outside the
    context.

    The timer is started immediately as this function returns the context.

    This is done in order to prevent the current process from hanging
    indefinitely in case the stored data is too big and the server spends more
    time processing it that what the network connection would stay alive for.

    The fact that this works is **NOT GUARANTEED**! In some cases, based on
    likely the kernel version, its implementation, and the exact network
    topology, the client may enter an *UNINTERRUPTIBLE* sleep ('D') at which
    point signals *MAY* not be accurately received. However, manual testing
    revealbed that resurrection of hung clients is possible even if the process
    is shown as "uninterruptible" by simply killing it from the outside.

    This is a **TEMPORARY** measure to alleviate hangs until the proper
    "pollable asynchronous store" feature is implemented, see:
    http://github.com/Ericsson/codechecker/issues/3672
    """
    def _signal_handler(sig: int, _):
        if sig == trap:
            signal.signal(trap, signal.SIG_DFL)
            raise WatchdogError(
                timeout,
                f"Timeout watchdog hit {timeout.total_seconds()} "
                f"seconds ({str(timeout)})")

    pid = os.getpid()
    timer = Timer(timeout.total_seconds(),
                  lambda: os.kill(pid, trap))
    timer.name = "StoreTimeoutWatcher"
    LOG.debug("Set up timer for %d seconds (%s) for PID %d",
              timeout.total_seconds(), str(timeout), pid)
    try:
        signal.signal(trap, _signal_handler)
        timer.start()
        yield timer
    except Exception as e:
        LOG.debug("External exception within timeout-sensing context: %s",
                  str(e))
        raise e
    finally:
        timer.cancel()
        signal.signal(trap, signal.SIG_DFL)
        LOG.debug("Timeout timer of %d seconds (%s) for PID %d stopped.",
                  timeout.total_seconds(), str(timeout), pid)


def main(args):
    """
    Store the defect results in the specified input list as bug reports in the
    database.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

    try:
        cmd_config.check_config_file(args)
    except FileNotFoundError as fnerr:
        LOG.error(fnerr)
        sys.exit(1)

    if not host_check.check_zlib():
        raise ModuleNotFoundError("zlib is not available on the system!")

    # To ensure the help message prints the default folder properly,
    # the 'default' for 'args.input' is a string, not a list.
    # But we need lists for the foreach here to work.
    if isinstance(args.input, str):
        args.input = [args.input]

    args.input = [os.path.abspath(i) for i in args.input]

    for input_path in args.input:
        if not os.path.exists(input_path):
            LOG.error("Input path '%s' does not exist!", input_path)
            sys.exit(1)

    if 'name' not in args:
        LOG.debug("Generating name for analysis...")
        generated = __get_run_name(args.input)
        if generated:
            setattr(args, 'name', generated)
        else:
            LOG.error("No suitable name was found in the inputs for the "
                      "analysis run. Please specify one by passing argument "
                      "--name run_name in the invocation.")
            sys.exit(2)  # argparse returns error code 2 for bad invocations.

    LOG.info("Storing analysis results for run '%s'", args.name)

    if 'force' in args:
        LOG.info("argument --force was specified: the run with name '%s' will "
                 "be deleted", args.name)

    # Setup connection to the remote server.
    client = libclient.setup_client(args.product_url)
    protocol, host, port, product_name = \
        product.split_product_url(args.product_url)
    prod_client = libclient.setup_product_client(protocol,
                                                 host,
                                                 port,
                                                 product_name=product_name)

    # If the --temp_dir argument is specified set use that,
    # else use the analyze result folder
    temp_dir_path: str = args.temp_dir if args.temp_dir else args.input[0]
    if not os.access(temp_dir_path, os.W_OK):
        # If the specified folder isn't writeable; fallback to /tmp/
        LOG.debug("'%s' is readonly, falling back to /tmp", temp_dir_path)
        temp_dir_path = "/tmp"
    try:
        temp_dir = tempfile.mkdtemp(suffix="-store", dir=temp_dir_path)
        LOG.debug(f"{temp_dir} directory created successfully!")
    except PermissionError:
        LOG.error(f"Permission denied! You do not have sufficient "
                  f"permissions to create the {temp_dir} "
                  "temporary directory.")
        sys.exit(1)

    zip_file_handle, zip_file = tempfile.mkstemp(suffix=".zip", dir=temp_dir)
    LOG.debug("Will write mass store ZIP to '%s'...", zip_file)

    try:
        context = webserver_context.get_context()

        LOG.debug("Assembling zip file.")
        try:
            assemble_zip(args.input,
                         zip_file,
                         client,
                         prod_client,
                         context.checker_labels,
                         temp_dir_path)
        except ReportLimitExceedError:
            sys.exit(1)
        except Exception as ex:
            print(ex)
            import traceback
            traceback.print_exc()
            LOG.error("Failed to assemble zip file.")
            sys.exit(1)

        zip_size = os.stat(zip_file).st_size
        if zip_size > MAX_UPLOAD_SIZE:
            LOG.error("The result list to upload is too big (max: %s): %s.",
                      format_size(MAX_UPLOAD_SIZE), format_size(zip_size))
            sys.exit(1)

        b64zip = ""
        with open(zip_file, 'rb') as zf:
            b64zip = base64.b64encode(zf.read()).decode("utf-8")
        if len(b64zip) == 0:
            LOG.info("Zip content is empty, nothing to store!")
            sys.exit(1)

        trim_path_prefixes = args.trim_path_prefix if \
            'trim_path_prefix' in args else None

        description = args.description if 'description' in args else None

        LOG.info("Storing results to the server ...")

        if strtobool(os.environ.get('CC_FORCE_SYNC_STORE', 'no')):
            try:
                with _timeout_watchdog(timedelta(hours=1),
                                       signal.SIGUSR1):
                    client.massStoreRun(args.name,
                                        args.tag if 'tag' in args else None,
                                        str(context.version),
                                        b64zip,
                                        'force' in args,
                                        trim_path_prefixes,
                                        description)
            except WatchdogError as we:
                LOG.warning("%s", str(we))

                # Showing parts of the exception stack is important here.
                # We **WANT** to see that the timeout happened during a wait on
                # Thrift reading from the TCP connection (something deep in the
                # Python library code at "sock.recv_into").
                import traceback
                _, _, tb = sys.exc_info()
                frames = traceback.extract_tb(tb)
                first, last = frames[0], frames[-2]
                formatted_frames = traceback.format_list([first, last])
                fmt_first, fmt_last = formatted_frames[0], formatted_frames[1]
                LOG.info("Timeout was triggered during:\n%s", fmt_first)
                LOG.info("Timeout interrupted this low-level operation:\n%s",
                         fmt_last)

                LOG.error(
                    "Timeout!"
                    "\n\tThe server's reply did not arrive after "
                    "%d seconds (%s) elapsed since the server-side "
                    "processing began."
                    "\n\n\tThis does *NOT* mean that there was an issue "
                    "with the run you were storing!"
                    "\n\tThe server might still be processing the results..."
                    "\n\tHowever, it is more likely that the "
                    "server had already finished, but the client did not "
                    "receive a response."
                    "\n\tUsually, this is caused by the underlying TCP "
                    "connection failing to signal a low-level disconnect."
                    "\n\tClients potentially hanging indefinitely in these "
                    "scenarios is an unfortunate and known issue."
                    "\n\t\tSee http://github.com/Ericsson/codechecker/"
                    "issues/3672 for details!"
                    "\n\n\tThis error here is a temporary measure to ensure "
                    "an infinite hang is replaced with a well-explained "
                    "timeout."
                    "\n\tA more proper solution will be implemented in a "
                    "subsequent version of CodeChecker.",
                    we.timeout.total_seconds(), str(we.timeout))
                sys.exit(1)

            if client.allowsStoringAnalysisStatistics():
                store_analysis_statistics(client, args.input, args.name)
        else:
            task_token: str = client.massStoreRunAsynchronous(
                b64zip,
                SubmittedRunOptions(
                    runName=args.name,
                    tag=args.tag if "tag" in args else None,
                    version=str(context.version),
                    force="force" in args,
                    trimPathPrefixes=trim_path_prefixes,
                    description=description)
                )
            LOG.info("Reports submitted to the server for processing.")

            if client.allowsStoringAnalysisStatistics():
                store_analysis_statistics(client, args.input, args.name)

            if "detach" in args:
                LOG.warning(
                    "Exiting the 'store' subcommand as '--detach' was "
                    "specified: not waiting for the result of the store "
                    "operation.\n"
                    "The server might not have finished processing "
                    "everything at this point, so do NOT rely on querying "
                    "the results just yet!\n"
                    "To await the completion of the processing later, "
                    "you can execute:\n\n"
                    "\tCodeChecker cmd serverside-tasks --token %s "
                    "--await",
                    task_token)
                # Print the token to stdout as well, so scripts can use
                # "--detach" meaningfully.
                print(task_token)
                return

            task_client = libclient.setup_task_client(protocol, host, port)
            task_status: str = await_task_termination(
                LOG, task_token, task_api_client=task_client)

            if task_status == "COMPLETED":
                LOG.info("Storing the reports finished successfully.")
            else:
                LOG.error(
                    "Storing the reports failed! "
                    "The job terminated in status '%s'. "
                    "The comments associated with the failure are:\n\n%s",
                    task_status,
                    task_client.getTaskInfo(task_token).comments)
                sys.exit(1)

    except Exception as ex:
        import traceback
        traceback.print_exc()
        LOG.error("Storing the reports failed: %s", str(ex))
        sys.exit(1)
    finally:
        os.close(zip_file_handle)
        os.remove(zip_file)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
