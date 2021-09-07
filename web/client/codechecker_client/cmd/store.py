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
import hashlib
import json
import os
import sys
import tempfile
from typing import Dict, List, Set, Tuple
import zipfile
import zlib

from concurrent.futures import ProcessPoolExecutor

from collections import namedtuple

from codechecker_api.codeCheckerDBAccess_v6.ttypes import StoreLimitKind
from codechecker_api_shared.ttypes import RequestFailed, ErrorCode

from codechecker_client import client as libclient
from codechecker_common import arg, logger, plist_parser, util, cmd_config
from codechecker_common.report import Report
from codechecker_common.output import twodim
from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler
from codechecker_report_hash.hash import HashType, replace_report_hash

from codechecker_web.shared import webserver_context, host_check
from codechecker_web.shared.env import get_default_workspace

try:
    from codechecker_client.blame_info import assemble_blame_info
except ImportError:
    pass

LOG = logger.get_logger('system')

MAX_UPLOAD_SIZE = 1 * 1024 * 1024 * 1024  # 1GiB


"""Minimal required information for a report position in a source file.

line: line number where the report was generated
fileidx: is the file index in the generated plist report file
filepath: the absolute path to the souce file
"""
ReportLineInfo = namedtuple('ReportLineInfo',
                            ['line', 'fileidx', 'filepath'])


"""Contains information about the report file after parsing.

store_it: True if every information is availabe and the
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


def sizeof_fmt(num, suffix='B'):
    """
    Pretty print storage units.
    Source: https://stackoverflow.com/questions/1094841/
        reusable-library-to-get-human-readable-version-of-file-size
    """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


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
                             "stored. So if you have /a/b/c/x.cpp and "
                             "/a/b/c/y.cpp then by removing \"/a/b/\" prefix "
                             "will store files like c/x.cpp and c/y.cpp. "
                             "If multiple prefix is given, the longest match "
                             "will be removed.")

    parser.add_argument('--config',
                        dest='config_file',
                        required=False,
                        help="R|Allow the configuration from an explicit JSON "
                             "based configuration file. The values configured "
                             "in the config file will overwrite the values "
                             "set in the command line. The format of "
                             "configuration file is:\n"
                             "{\n"
                             "  \"store\": [\n"
                             "    \"--name=run_name\",\n"
                             "    \"--tag=my_tag\",\n"
                             "    \"--url=http://codechecker.my/MyProduct\"\n"
                             "  ]\n"
                             "}.")

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

    # Try to create a name from the metada JSON(s).
    names = set()
    for input_path in input_list:
        metafile = os.path.join(input_path, "metadata.json")
        if os.path.isdir(input_path) and os.path.exists(metafile):
            metajson = util.load_json_or_empty(metafile)

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
    else:
        return False


def res_handler(results):
    """
    Summary about the parsing and storage results.
    """
    LOG.info("Finished processing and storing reports.")
    LOG.info("Failed: %d/%d", results.count(1), len(results))
    LOG.info("Successful %d/%d", results.count(0), len(results))


def collect_report_files(inputs: List[str]) -> Set[str]:
    """
    Collect all the plist report files in the inputs directories recursively.
    """
    report_files: Set[str] = set()

    def is_report_file(file_path):
        """ True if the given file is a report file. """
        return file_path.endswith(".plist")

    for input_path in inputs:
        if os.path.isfile(input_path):
            if is_report_file(input_path):
                report_files.add(input_path)
        else:
            for root_dir_path, _, files in os.walk(input_path):
                for f in files:
                    file_path = os.path.join(root_dir_path, f)
                    if is_report_file(file_path):
                        report_files.add(file_path)

    return report_files


def parse_report_file(plist_file: str) \
        -> Tuple[Dict[int, str], List[Report]]:
    """Parse a plist report file and return the list of reports and the
    list of source files mentioned in the report file.
    """
    files = {}
    reports = []

    try:
        files, reports = plist_parser.parse_plist_file(plist_file)
    except Exception as ex:
        import traceback
        traceback.print_stack()
        LOG.error('Parsing the plist failed: %s', str(ex))
    finally:
        return files, reports


def collect_file_info(files: Dict[int, str]) -> Dict:
    """Collect file information about given list of files like:
       - last modification time
       - content hash
       If the file is missing the corresponding data will
       be empty.
    """
    res = {}
    for sf in files.values():
        res[sf] = {}
        if os.path.isfile(sf):
            res[sf]["hash"] = get_file_content_hash(sf)
            res[sf]["mtime"] = util.get_last_mod_time(sf)

    return res


def find_files(directory, file_name):
    """Return the list of files with the exact name match under
    the given directory.
    """
    res = set()
    for input_path in directory:
        input_path = os.path.abspath(input_path)

        if not os.path.exists(input_path):
            return res

        _, _, files = next(os.walk(input_path), ([], [], []))

        for f in files:
            if f == file_name:
                res.add(os.path.join(input_path, f))
    return res


def check_missing_files(source_file_info):
    """Return a set of the missing files from the source_file_info dict.
    """
    return {k for k, v in source_file_info.items() if not bool(v)}


def overwrite_cppcheck_report_hash(reports, plist_file):
    """CppCheck generates a '0' value for the bug hash.
    In case all of the reports in a plist file contain only
    a hash with '0' value overwrite the hash values in the
    plist report files with a context free hash value.
    """
    rep_hash = [rep.report_hash == '0' for rep in reports]
    if all(rep_hash):
        replace_report_hash(plist_file, HashType.CONTEXT_FREE)
        return True
    return False


def get_report_data(reports):
    """Return the minimal required report information to be able
    to collect review comments from the source code.
    """
    report_main = []
    for report in reports:
        last_report_event = report.bug_path[-1]
        file_path_index = last_report_event['location']['file']
        report_line = last_report_event['location']['line']
        report_main.append(ReportLineInfo(report_line,
                                          file_path_index,
                                          ""))
    return report_main


def scan_for_review_comment(job):
    """Scan a file for review comments returns
    all the found review comments.
    """
    file_path, lines = job
    sc_handler = SourceCodeCommentHandler()
    comments = []
    with open(file_path, mode='r',
              encoding='utf-8',
              errors='ignore') as sf:
        comments, misspelled_comments = \
                sc_handler.scan_source_line_comments(sf, lines)

        if misspelled_comments:
            LOG.warning("There are misspelled review status comments in %s",
                        file_path)
        for mc in misspelled_comments:
            LOG.warning(mc)

    return comments


def get_source_file_with_comments(jobs, zip_iter=map):
    """
    Get source files where there is any codechecker review comment at the main
    report positions.
    """
    files_with_comment = set()

    for job, comments in zip(jobs,
                             zip_iter(scan_for_review_comment, jobs)):
        file_path, _ = job
        if comments:
            files_with_comment.add(file_path)

    return files_with_comment


def filter_source_files_with_comments(source_file_info, main_report_positions):
    """Collect the source files where there is any codechecker review
    comment at the main report positions.
    """
    jobs = []
    for file_path, v in source_file_info.items():
        if not bool(v):
            # missing file
            continue
        lines = [rep.line for rep in main_report_positions
                 if rep.filepath == file_path]

        jobs.append((file_path, lines))

    # Currently ProcessPoolExecutor fails completely in windows.
    # Reason is most likely combination of venv and fork() not
    # being present in windows, so stuff like setting up
    # PYTHONPATH in parent CodeChecker before store is executed
    # are lost.
    if sys.platform == "win32":
        return get_source_file_with_comments(jobs)
    else:
        with ProcessPoolExecutor() as executor:
            return get_source_file_with_comments(jobs, executor.map)


def parse_collect_plist_info(plist_file):
    """Parse one plist report file and collect information
    about the source files mentioned in the report file.
    """

    source_files, reports = parse_report_file(plist_file)

    if len(source_files) == 0:
        # If there is no source in the plist we will not upload
        # it to the server.
        LOG.debug("Skip empty plist file: %s", plist_file)
        rli = ReportFileInfo(store_it=False, main_report_positions=[])
        sfir = SourceFilesInReport(source_info={},
                                   missing=set(),
                                   changed_since_report_gen=set())
        return rli, sfir

    source_info = collect_file_info(source_files)

    missing_files = set()
    missing_files = check_missing_files(source_info)
    if missing_files:
        LOG.warning("Skipping '%s' because it refers "
                    "the following missing source files: %s",
                    plist_file, missing_files)
        for mf in missing_files:
            missing_files.add(mf)

        rli = ReportFileInfo(store_it=False, main_report_positions=[])
        sfir = SourceFilesInReport(source_info=source_info,
                                   missing=missing_files,
                                   changed_since_report_gen=set())
        return rli, sfir

    if overwrite_cppcheck_report_hash(reports, plist_file):
        # If overwrite was needed parse it back again to update the hashes.
        source_files, reports = parse_report_file(plist_file)

    main_report_positions = []
    rdata = get_report_data(reports)
    # Replace the file index values to source file path.
    for rda in rdata:
        rda = rda._replace(filepath=source_files[rda.fileidx])
        main_report_positions.append(rda)

    plist_mtime = util.get_last_mod_time(plist_file)

    changed_files = set()
    # Check if any source file corresponding to a plist
    # file changed since the plist file was generated.
    for k, v in source_info.items():
        if bool(v):
            if v['mtime'] > plist_mtime:
                changed_files.add(k)
    rli = ReportFileInfo(store_it=True,
                         main_report_positions=main_report_positions)
    sfir = SourceFilesInReport(source_info=source_info,
                               missing=missing_files,
                               changed_since_report_gen=changed_files)

    return rli, sfir


def parse_report_files(report_files: Set[str], zip_iter=map):
    """Parse and collect source code information mentioned in a report file.

    Collect any mentioned source files wich are missing or changed
    since the report generation. If there are missing or changed files
    the report will not be stored.
    """

    files_to_compress = set()
    source_file_info = {}
    main_report_positions = []
    changed_files = set()
    missing_source_files = set()

    for report_f, v in zip(report_files,
                           zip_iter(parse_collect_plist_info,
                                    report_files)):

        report_file_info, source_in_reports = v

        if report_file_info.store_it:
            files_to_compress.add(report_f)

        source_file_info.update(source_in_reports.source_info)
        changed_files = \
            changed_files | source_in_reports.changed_since_report_gen
        main_report_positions.extend(
            report_file_info.main_report_positions)
        missing_source_files = \
            missing_source_files | source_in_reports.missing

    return (source_file_info,
            main_report_positions,
            files_to_compress,
            changed_files,
            missing_source_files)


def assemble_zip(inputs, zip_file, client):
    """Collect and compress report and source files, together with files
    contanining analysis related information into a zip file which
    will be sent to the server.
    """
    report_files = collect_report_files(inputs)

    LOG.debug("Processing report files ...")

    # Currently ProcessPoolExecutor fails completely in windows.
    # Reason is most likely combination of venv and fork() not
    # being present in windows, so stuff like setting up
    # PYTHONPATH in parent CodeChecker before store is executed
    # are lost.
    if sys.platform == "win32":
        (source_file_info,
         main_report_positions,
         files_to_compress,
         changed_files,
         missing_source_files) = parse_report_files(report_files)
    else:
        with ProcessPoolExecutor() as executor:
            (source_file_info,
             main_report_positions,
             files_to_compress,
             changed_files,
             missing_source_files) = parse_report_files(report_files,
                                                        executor.map)

    LOG.info("Processing report files done.")

    if changed_files:
        changed_files = '\n'.join([' - ' + f for f in changed_files])
        LOG.warning("The following source file contents changed since the "
                    "latest analysis:\n%s\nPlease analyze your project "
                    "again to update the reports!", changed_files)
        sys.exit(1)

    hash_to_file = {}
    # There can be files with same hash,
    # but different path.
    file_to_hash = {}

    for source_file, info in source_file_info.items():
        if bool(info):
            file_to_hash[source_file] = info['hash']
            hash_to_file[info['hash']] = source_file

    LOG.info("Collecting review comments ...")
    files_with_comment = \
        filter_source_files_with_comments(source_file_info,
                                          main_report_positions)

    LOG.info("Collecting review comments done.")
    file_hash_with_review_status = set()
    for file_path in files_with_comment:
        file_hash = file_to_hash.get(file_path)
        if file_hash:
            file_hash_with_review_status.add(file_hash)

    for input_dir_path in inputs:
        for root_dir_path, _, _ in os.walk(input_dir_path):
            metadata_file_path = os.path.join(root_dir_path, 'metadata.json')
            if os.path.exists(metadata_file_path):
                files_to_compress.add(metadata_file_path)

            skip_file_path = os.path.join(root_dir_path, 'skip_file')
            if os.path.exists(skip_file_path):
                files_to_compress.add(skip_file_path)

    file_hashes = list(hash_to_file.keys())

    LOG.info("Get missing file content hashes from the server...")
    necessary_hashes = client.getMissingContentHashes(file_hashes) \
        if file_hashes else []
    LOG.info("Get missing file content hashes done.")

    if not hash_to_file:
        LOG.warning("There is no report to store. After uploading these "
                    "results the previous reports become resolved.")

    LOG.debug("Building report zip file.")
    with zipfile.ZipFile(zip_file, 'a',
                         allowZip64=True) as zipf:
        # Add the files to the zip which will be sent to the server.
        for ftc in files_to_compress:
            _, filename = os.path.split(ftc)

            # Create a unique report directory name.
            report_dir_name = \
                hashlib.md5(os.path.dirname(ftc).encode('utf-8')).hexdigest()

            zip_target = \
                os.path.join('reports', report_dir_name, filename)

            zipf.write(ftc, zip_target)

        collected_file_paths = []
        for f, h in file_to_hash.items():
            if h in necessary_hashes or h in file_hash_with_review_status:
                LOG.debug("File contents for '%s' needed by the server", f)

                file_path = os.path.join('root', f.lstrip('/'))
                collected_file_paths.append(f)

                try:
                    zipf.getinfo(file_path)
                except KeyError:
                    zipf.write(f, file_path)

        if collected_file_paths:
            LOG.info("Collecting blame information for source files...")
            try:
                if assemble_blame_info(zipf, collected_file_paths):
                    LOG.info("Collecting blame information done.")
                else:
                    LOG.info("No blame information found for source files.")
            except NameError:
                LOG.warning(
                    "Collecting blame information has been failed. Make sure "
                    "'git' is available on your system to hide this warning "
                    "message.")

        zipf.writestr('content_hashes.json', json.dumps(file_to_hash))

    # Compressing .zip file
    with open(zip_file, 'rb') as source:
        compressed = zlib.compress(source.read(),
                                   zlib.Z_BEST_COMPRESSION)

    with open(zip_file, 'wb') as target:
        target.write(compressed)

    LOG.debug("[ZIP] Mass store zip written at '%s'", zip_file)

    if missing_source_files:
        LOG.warning("Missing source files: \n%s", '\n'.join(
            [" - " + f_ for f_ in missing_source_files]))

    LOG.debug("Building report zip done.")


def should_be_zipped(input_file, input_files):
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
                              sizeof_fmt(compilation_db_size))
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
                                  sizeof_fmt(failure_zip_limit))
                        break
                    else:
                        LOG.debug("Copying failure zip file '%s' to analyzer "
                                  "statistics ZIP...", failure_zip)
                        statistics_files.append(failure_zip)
                        has_failed_zip = True

        return statistics_files if has_failed_zip else []


def storing_analysis_statistics(client, inputs, run_name):
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
            return False

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
        raise Exception("zlib is not available on the system!")

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

    LOG.info("Storing analysis results for run '" + args.name + "'")

    if 'force' in args:
        LOG.info("argument --force was specified: the run with name '" +
                 args.name + "' will be deleted.")

    # Setup connection to the remote server.
    client = libclient.setup_client(args.product_url)

    zip_file_handle, zip_file = tempfile.mkstemp('.zip')
    LOG.debug("Will write mass store ZIP to '%s'...", zip_file)

    try:
        LOG.debug("Assembling zip file.")
        try:
            assemble_zip(args.input, zip_file, client)
        except Exception as ex:
            print(ex)
            import traceback
            traceback.print_exc()
            LOG.error("Failed to assemble zip file.")
            sys.exit(1)

        zip_size = os.stat(zip_file).st_size
        if zip_size > MAX_UPLOAD_SIZE:
            LOG.error("The result list to upload is too big (max: %s): %s.",
                      sizeof_fmt(MAX_UPLOAD_SIZE), sizeof_fmt(zip_size))
            sys.exit(1)

        b64zip = ""
        with open(zip_file, 'rb') as zf:
            b64zip = base64.b64encode(zf.read()).decode("utf-8")
        if len(b64zip) == 0:
            LOG.info("Zip content is empty, nothing to store!")
            sys.exit(1)

        context = webserver_context.get_context()

        trim_path_prefixes = args.trim_path_prefix if \
            'trim_path_prefix' in args else None

        description = args.description if 'description' in args else None

        LOG.info("Storing results (%s) to the server...", sizeof_fmt(zip_size))

        client.massStoreRun(args.name,
                            args.tag if 'tag' in args else None,
                            str(context.version),
                            b64zip,
                            'force' in args,
                            trim_path_prefixes,
                            description)

        # Storing analysis statistics if the server allows them.
        if client.allowsStoringAnalysisStatistics():
            storing_analysis_statistics(client, args.input, args.name)

        LOG.info("Storage finished successfully.")
    except RequestFailed as reqfail:
        if reqfail.errorCode == ErrorCode.SOURCE_FILE:
            header = ['File', 'Line', 'Checker name']
            table = twodim.to_str(
                'table', header, [c.split('|') for c in reqfail.extraInfo])
            LOG.warning("Setting the review statuses for some reports failed "
                        "because of non valid source code comments: "
                        "%s\n %s", reqfail.message, table)
        sys.exit(1)
    except Exception as ex:
        import traceback
        traceback.print_stack()
        LOG.info("Storage failed: %s", str(ex))
        sys.exit(1)
    finally:
        os.close(zip_file_handle)
        os.remove(zip_file)
