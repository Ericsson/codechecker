# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helpers to store analysis reports.
"""

import base64
from datetime import datetime
from hashlib import sha256
import os
import zlib

import sqlalchemy

import codechecker_api_shared
from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from codechecker_common.logger import get_logger
from codechecker_common.util import load_json_or_empty

from ..database.run_db_model import AnalyzerStatistic, \
    BugPathEvent, BugReportPoint, File, Run, RunHistory, Report, FileContent, \
    ExtendedReportData

from .thrift_enum_helper import report_extended_data_type_str

LOG = get_logger('system')


def metadata_info(metadata_file):
    check_commands = []
    check_durations = []
    cc_version = None
    analyzer_statistics = {}
    checkers = {}

    if not os.path.isfile(metadata_file):
        return check_commands, check_durations, cc_version, \
               analyzer_statistics, checkers

    metadata_dict = load_json_or_empty(metadata_file, {})

    if 'command' in metadata_dict:
        check_commands.append(metadata_dict['command'])
    if 'timestamps' in metadata_dict:
        check_durations.append(
            float(metadata_dict['timestamps']['end'] -
                  metadata_dict['timestamps']['begin']))

    # Get CodeChecker version.
    cc_version = metadata_dict.get('versions', {}).get('codechecker')

    # Get analyzer statistics.
    analyzer_statistics = metadata_dict.get('analyzer_statistics', {})

    checkers = metadata_dict.get('checkers', {})

    return check_commands, check_durations, cc_version, analyzer_statistics, \
        checkers


def collect_paths_events(report, file_ids, files):
    """
    This function creates the BugPathPos and BugPathEvent objects which belong
    to a report.

    report -- A report object from the parsed plist file.
    file_ids -- A dictionary which maps the file paths to file IDs in the
                database.
    files -- A list containing the file paths from the parsed plist file. The
             order of this list must be the same as in the plist file.

    #TODO Multiple ranges could belong to an event or control node.
    Only the first range from the list of ranges is stored into the
    database. Further improvement can be to store and view all ranges
    if there are more than one.
    """
    bug_paths = []
    bug_events = []
    bug_extended_data = []

    events = [i for i in report.bug_path if i.get('kind') == 'event']

    # Create remaining data for bugs and send them to the server.  In plist
    # file the source and target of the arrows are provided as starting and
    # ending ranges of the arrow. The path A->B->C is given as A->B and
    # B->C, thus range B is provided twice. So in the loop only target
    # points of the arrows are stored, and an extra insertion is done for
    # the source of the first arrow before the loop.
    report_path = [i for i in report.bug_path if i.get('kind') == 'control']

    if report_path:
        start_range = report_path[0]['edges'][0]['start']
        start1_line = start_range[0]['line']
        start1_col = start_range[0]['col']
        start2_line = start_range[1]['line']
        start2_col = start_range[1]['col']
        source_file_path = files[start_range[1]['file']]
        bug_paths.append(ttypes.BugPathPos(
            start1_line,
            start1_col,
            start2_line,
            start2_col,
            file_ids[source_file_path]))

    for path in report_path:
        try:
            end_range = path['edges'][0]['end']
            end1_line = end_range[0]['line']
            end1_col = end_range[0]['col']
            end2_line = end_range[1]['line']
            end2_col = end_range[1]['col']
            source_file_path = files[end_range[1]['file']]
            bug_paths.append(ttypes.BugPathPos(
                end1_line,
                end1_col,
                end2_line,
                end2_col,
                file_ids[source_file_path]))
        except IndexError:
            # Edges might be empty nothing can be stored.
            continue

    for event in events:
        file_path = files[event['location']['file']]

        start_loc = event['location']
        end_loc = event['location']
        # Range can provide more precise location information.
        # Use that if available.
        ranges = event.get("ranges")
        if ranges:
            start_loc = ranges[0][0]
            end_loc = ranges[0][1]

        bug_events.append(ttypes.BugPathEvent(
            start_loc['line'],
            start_loc['col'],
            end_loc['line'],
            end_loc['col'],
            event['message'],
            file_ids[file_path]))

    for macro in report.macro_expansions:
        if not macro['expansion']:
            continue

        file_path = files[macro['location']['file']]

        start_loc = macro['location']
        end_loc = macro['location']
        # Range can provide more precise location information.
        # Use that if available.
        ranges = macro.get("ranges")
        if ranges:
            start_loc = ranges[0][0]
            end_loc = ranges[0][1]

        bug_extended_data.append(ttypes.ExtendedReportData(
            ttypes.ExtendedReportDataType.MACRO,
            start_loc['line'],
            start_loc['col'],
            end_loc['line'],
            end_loc['col'],
            macro['expansion'],
            file_ids[file_path]))

    for note in report.notes:
        if not note['message']:
            continue

        file_path = files[note['location']['file']]

        start_loc = note['location']
        end_loc = note['location']
        # Range can provide more precise location information.
        # Use that if available.
        ranges = note.get("ranges")
        if ranges:
            start_loc = ranges[0][0]
            end_loc = ranges[0][1]

        bug_extended_data.append(ttypes.ExtendedReportData(
            ttypes.ExtendedReportDataType.NOTE,
            start_loc['line'],
            start_loc['col'],
            end_loc['line'],
            end_loc['col'],
            note['message'],
            file_ids[file_path]))

    return bug_paths, bug_events, bug_extended_data,


def store_bug_events(session, bugevents, report_id):
    """
    """
    for i, event in enumerate(bugevents):
        bpe = BugPathEvent(event.startLine,
                           event.startCol,
                           event.endLine,
                           event.endCol,
                           i,
                           event.msg,
                           event.fileId,
                           report_id)
        session.add(bpe)


def store_bug_path(session, bugpath, report_id):
    for i, piece in enumerate(bugpath):
        brp = BugReportPoint(piece.startLine,
                             piece.startCol,
                             piece.endLine,
                             piece.endCol,
                             i,
                             piece.fileId,
                             report_id)
        session.add(brp)


def store_extended_bug_data(session, extended_data, report_id):
    """
    Add extended bug data objects to the database session.
    """
    for data in extended_data:
        data_type = report_extended_data_type_str(data.type)
        red = ExtendedReportData(data.startLine,
                                 data.startCol,
                                 data.endLine,
                                 data.endCol,
                                 data.message,
                                 data.fileId,
                                 report_id,
                                 data_type)
        session.add(red)


def is_same_event_path(report_id, events, session):
    """
    Checks if the given event path is the same as the one in the
    events argument.
    """
    try:
        q = session.query(BugPathEvent) \
            .filter(BugPathEvent.report_id == report_id) \
            .order_by(BugPathEvent.order)

        for i, point2 in enumerate(q):
            if i == len(events):
                return False

            point1 = events[i]

            file1name = os.path.basename(session.query(File).
                                         get(point1.fileId).filepath)
            file2name = os.path.basename(session.query(File).
                                         get(point2.file_id).filepath)

            if point1.startCol != point2.col_begin or \
                    point1.endCol != point2.col_end or \
                    file1name != file2name or \
                    point1.msg != point2.msg:
                return False

        return True

    except Exception as ex:
        raise codechecker_api_shared.ttypes.RequestFailed(
            codechecker_api_shared.ttypes.ErrorCode.GENERAL,
            str(ex))


def addCheckerRun(session, command, name, tag, username,
                  run_history_time, version, force, codechecker_version,
                  statistics, description):
    """
    Store checker run related data to the database.
    By default updates the results if name already exists.
    Using the force flag removes existing analysis results for a run.
    """
    try:
        LOG.debug("adding checker run")

        run = session.query(Run).filter(Run.name == name).one_or_none()

        if run and force:
            # Clean already collected results.
            if not run.can_delete:
                # Deletion is already in progress.
                msg = "Can't delete " + str(run.id)
                LOG.debug(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    msg)

            LOG.info('Removing previous analysis results ...')
            session.delete(run)
            # Not flushing after delete leads to a constraint violation error
            # later, when adding run entity with the same name as the old one.
            session.flush()

            checker_run = Run(name, version, command)
            session.add(checker_run)
            session.flush()
            run_id = checker_run.id

        elif run:
            # There is already a run, update the results.
            run.date = datetime.now()
            run.command = command
            run.duration = -1
            session.flush()
            run_id = run.id
        else:
            # There is no run create new.
            checker_run = Run(name, version, command)
            session.add(checker_run)
            session.flush()
            run_id = checker_run.id

        # Add run to the history.
        LOG.debug("adding run to the history")

        if tag is not None:
            run_history = session.query(RunHistory) \
                .filter(RunHistory.run_id == run_id,
                        RunHistory.version_tag == tag) \
                .one_or_none()

            if run_history:
                run_history.version_tag = None
                session.add(run_history)

        compressed_command = zlib.compress(command.encode("utf-8"),
                                           zlib.Z_BEST_COMPRESSION)
        run_history = RunHistory(run_id, tag, username, run_history_time,
                                 compressed_command, codechecker_version,
                                 description)
        session.add(run_history)
        session.flush()
        LOG.debug("command store done")
        # Create entry for analyzer statistics.
        for analyzer_type, res in statistics.items():
            analyzer_version = res.get('version', None)
            successful = res.get('successful')
            failed = res.get('failed')
            failed_sources = res.get('failed_sources')

            if analyzer_version:
                LOG.debug(analyzer_version)
                analyzer_version \
                    = zlib.compress(analyzer_version.encode('utf-8'),
                                    zlib.Z_BEST_COMPRESSION)

            LOG.debug("analyzer version compressed")
            compressed_files = None
            if failed_sources:
                if version == '6.9.0':
                    failed_sources = ['Unavailable in CodeChecker 6.9.0!']

                compressed_files = zlib.compress(
                    '\n'.join(failed_sources).encode('utf-8'),
                    zlib.Z_BEST_COMPRESSION)

            LOG.debug("failed source compressed")
            analyzer_statistics = AnalyzerStatistic(run_history.id,
                                                    analyzer_type,
                                                    analyzer_version,
                                                    successful,
                                                    failed,
                                                    compressed_files)
            LOG.debug("stats added to session")
            session.add(analyzer_statistics)

        session.flush()
        LOG.debug("stats store done")
        return run_id
    except Exception as ex:
        raise codechecker_api_shared.ttypes.RequestFailed(
            codechecker_api_shared.ttypes.ErrorCode.GENERAL,
            str(ex))


def finishCheckerRun(session, run_id):
    """
    """
    try:
        LOG.debug("Finishing checker run")
        run = session.query(Run).get(run_id)
        if not run:
            return False

        run.mark_finished()

        return True

    except Exception as ex:
        LOG.error(ex)
        return False


def setRunDuration(session, run_id, duration):
    """
    """
    try:
        run = session.query(Run).get(run_id)

        if not run:
            return False

        run.duration = duration
        return True
    except Exception as ex:
        LOG.error(ex)
        return False


def addReport(session,
              run_id,
              file_id,
              main_section,
              bugpath,
              events,
              bug_extended_data,
              detection_status,
              detection_time,
              severity_map,
              analyzer_name=None):
    """
    """
    try:

        checker_names = main_section['check_name'].split(',')
        # tidy checker name aliases are separated by a comma.
        checker_name = checker_names[0]
        severity_name = severity_map.get(checker_name)
        severity = ttypes.Severity._NAMES_TO_VALUES[severity_name]

        report = Report(run_id,
                        main_section['issue_hash_content_of_line_in_context'],
                        file_id,
                        main_section['description'],
                        checker_name or 'NOT FOUND',
                        main_section['category'],
                        main_section['type'],
                        main_section['location']['line'],
                        main_section['location']['col'],
                        severity,
                        detection_status,
                        detection_time,
                        len(events),
                        analyzer_name)

        session.add(report)
        session.flush()

        LOG.debug("storing bug path")
        store_bug_path(session, bugpath, report.id)
        LOG.debug("storing events")
        store_bug_events(session, events, report.id)
        LOG.debug("storing extended report data")
        store_extended_bug_data(session, bug_extended_data, report.id)

        return report.id

    except Exception as ex:
        raise codechecker_api_shared.ttypes.RequestFailed(
            codechecker_api_shared.ttypes.ErrorCode.GENERAL,
            str(ex))


def changePathAndEvents(session, run_id, report_path_map):
    report_ids = list(report_path_map.keys())

    session.query(BugPathEvent) \
        .filter(BugPathEvent.report_id.in_(report_ids)) \
        .delete(synchronize_session=False)

    session.query(BugReportPoint) \
        .filter(BugReportPoint.report_id.in_(report_ids)) \
        .delete(synchronize_session=False)

    for report_id, (bug_path, events) in report_path_map.items():
        store_bug_path(session, bug_path, report_id)
        store_bug_events(session, events, report_id)


def get_file_content(filepath, encoding):
    """Return the file content for the given filepath.

    If the client sent the file contents encoded decode
    the file content based on the encoding method.
    This encoding is optionally used during network transfer
    between the client an the server.
    """
    with open(filepath, 'rb') as source_file:
        content = source_file.read()

    if encoding == ttypes.Encoding.BASE64:
        content = base64.b64decode(content)
    return content


def addFileContent(session, filepath, source_file_name, content_hash,
                   encoding):
    """
    Add the necessary file contents. If the file is already stored in the
    database then its ID returns. If content_hash in None then this function
    calculates the content hash. Or if is available at the caller and is
    provided then it will not be calculated again.

    This function must not be called between addCheckerRun() and
    finishCheckerRun() functions when SQLite database is used! addCheckerRun()
    function opens a transaction which is closed by finishCheckerRun() and
    since SQLite doesn't support parallel transactions, this API call will
    wait until the other transactions finish. In the meantime the run adding
    transaction times out.
    """

    source_file_content = None
    if not content_hash:
        source_file_content = get_file_content(source_file_name, encoding)
        hasher = sha256()
        hasher.update(source_file_content)
        content_hash = hasher.hexdigest()

    file_content = session.query(FileContent).get(content_hash)
    if not file_content:
        if not source_file_content:
            source_file_content = get_file_content(source_file_name, encoding)
        try:
            compressed_content = zlib.compress(source_file_content,
                                               zlib.Z_BEST_COMPRESSION)
            fc = FileContent(content_hash, compressed_content)
            session.add(fc)
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            # Other transaction moght have added the same content in
            # the meantime.
            session.rollback()

    file_record = session.query(File) \
        .filter(File.content_hash == content_hash,
                File.filepath == filepath) \
        .one_or_none()
    if not file_record:
        try:
            file_record = File(filepath, content_hash)
            session.add(file_record)
            session.commit()
        except sqlalchemy.exc.IntegrityError as ex:
            LOG.error(ex)
            # Other transaction might have added the same file in the
            # meantime.
            session.rollback()
            file_record = session.query(File) \
                .filter(File.content_hash == content_hash,
                        File.filepath == filepath) \
                .one_or_none()

    return file_record.id


def addFileRecord(session, filepath, content_hash):
    """
    Add the necessary file record pointing to an already existing content.
    Returns the added file record id or None, if the content_hash is not found.

    This function must not be called between addCheckerRun() and
    finishCheckerRun() functions when SQLite database is used! addCheckerRun()
    function opens a transaction which is closed by finishCheckerRun() and
    since SQLite doesn't support parallel transactions, this API call will
    wait until the other transactions finish. In the meantime the run adding
    transaction times out.
    """
    file_record = session.query(File) \
        .filter(File.content_hash == content_hash,
                File.filepath == filepath) \
        .one_or_none()
    if file_record:
        return file_record.id
    try:
        file_record = File(filepath, content_hash)
        session.add(file_record)
        session.commit()
    except sqlalchemy.exc.IntegrityError as ex:
        LOG.error(ex)
        # Other transaction might have added the same file in the
        # meantime.
        session.rollback()
        file_record = session.query(File) \
            .filter(File.content_hash == content_hash,
                    File.filepath == filepath).one_or_none()

    return file_record.id if file_record else None
