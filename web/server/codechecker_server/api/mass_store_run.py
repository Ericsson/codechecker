# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import base64
import os
import sqlalchemy
import tempfile
import time
import zipfile
import zlib

from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, NamedTuple, Optional, Set

import codechecker_api_shared
from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from codechecker_common import plist_parser, skiplist_handler, util
from codechecker_common.logger import get_logger
from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler, SpellException, contains_codechecker_comment

from codechecker_report_hash.hash import get_report_path_hash

from ..database import db_cleanup
from ..database.config_db_model import Product
from ..database.database import DBSession
from ..database.run_db_model import AnalysisInfo, AnalyzerStatistic, \
    BugPathEvent, BugReportPoint, ExtendedReportData, File, FileContent, \
    Report, Run, RunHistory, RunLock
from ..metadata import checker_is_unavailable, get_analyzer_name, \
    MetadataInfoParser

from .report_server import ThriftRequestHandler
from .thrift_enum_helper import report_extended_data_type_str


LOG = get_logger('server')


# FIXME: when these types are introduced we need to use those.
SourceLineComments = List[Any]
ReportType = Any
MainSection = Dict


class PathEvents(NamedTuple):
    paths: List[ttypes.BugPathPos]
    events: List[ttypes.BugPathEvent]
    extended_data: List[ttypes.ExtendedReportData]


def unzip(b64zip: str, output_dir: str) -> int:
    """
    This function unzips the base64 encoded zip file. This zip is extracted
    to a temporary directory and the ZIP is then deleted. The function returns
    the size of the extracted decompressed zip file.
    """
    if len(b64zip) == 0:
        return 0

    with tempfile.NamedTemporaryFile(suffix='.zip') as zip_file:
        LOG.debug("Unzipping mass storage ZIP '%s' to '%s'...",
                  zip_file.name, output_dir)

        zip_file.write(zlib.decompress(base64.b64decode(b64zip)))
        with zipfile.ZipFile(zip_file, 'r', allowZip64=True) as zipf:
            try:
                zipf.extractall(output_dir)
                return os.stat(zip_file.name).st_size
            except Exception:
                LOG.error("Failed to extract received ZIP.")
                import traceback
                traceback.print_exc()
                raise
    return 0


def get_file_content(file_path: str) -> bytes:
    """Return the file content for the given filepath. """
    with open(file_path, 'rb') as f:
        return f.read()


def parse_codechecker_review_comment(
    source_file_name: str,
    report_line: int,
    checker_name: str
) -> SourceLineComments:
    """Parse the CodeChecker review comments from a source file at a given
    position.  Returns an empty list if there are no comments.
    """
    src_comment_data = []
    with open(source_file_name, encoding='utf-8', errors='ignore') as f:
        if contains_codechecker_comment(f):
            sc_handler = SourceCodeCommentHandler()
            try:
                src_comment_data = sc_handler.filter_source_line_comments(
                    f, report_line, checker_name)
            except SpellException as ex:
                LOG.warning("File %s contains %s", source_file_name, ex)

    return src_comment_data


def collect_paths_events(
    report: ReportType,
    file_ids: Dict[str, int],
    files: Dict[str, str]
) -> PathEvents:
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
    path_events = PathEvents([], [], [])

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
        path_events.paths.append(ttypes.BugPathPos(
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
            path_events.paths.append(ttypes.BugPathPos(
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

        path_events.events.append(ttypes.BugPathEvent(
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

        path_events.extended_data.append(ttypes.ExtendedReportData(
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

        path_events.extended_data.append(ttypes.ExtendedReportData(
            ttypes.ExtendedReportDataType.NOTE,
            start_loc['line'],
            start_loc['col'],
            end_loc['line'],
            end_loc['col'],
            note['message'],
            file_ids[file_path]))

    return path_events


def add_file_record(
    session: DBSession,
    file_path: str,
    content_hash: str
) -> Optional[int]:
    """
    Add the necessary file record pointing to an already existing content.
    Returns the added file record id or None, if the content_hash is not
    found.

    This function must not be called between add_checker_run() and
    finish_checker_run() functions when SQLite database is used!
    add_checker_run() function opens a transaction which is closed by
    finish_checker_run() and since SQLite doesn't support parallel
    transactions, this API call will wait until the other transactions
    finish. In the meantime the run adding transaction times out.
    """
    file_record = session.query(File) \
        .filter(File.content_hash == content_hash,
                File.filepath == file_path) \
        .one_or_none()

    if file_record:
        return file_record.id

    try:
        file_record = File(file_path, content_hash)
        session.add(file_record)
        session.commit()
    except sqlalchemy.exc.IntegrityError as ex:
        LOG.error(ex)
        # Other transaction might have added the same file in the
        # meantime.
        session.rollback()
        file_record = session.query(File) \
            .filter(File.content_hash == content_hash,
                    File.filepath == file_path).one_or_none()

    return file_record.id if file_record else None


class MassStoreRun:
    def __init__(
        self,
        report_server: ThriftRequestHandler,
        name: str,
        tag: Optional[str],
        version: Optional[str],
        b64zip: str,
        force: bool,
        trim_path_prefixes: Optional[List[str]],
        description: Optional[str]
    ):
        """ Initialize object. """
        self.__report_server = report_server

        self.__name = name
        self.__tag = tag
        self.__version = version
        self.__b64zip = b64zip
        self.__force = force
        self.__trim_path_prefixes = trim_path_prefixes
        self.__description = description

        self.__mips: Dict[str, MetadataInfoParser] = {}
        self.__analysis_info: Dict[str, AnalysisInfo] = {}
        self.__duration: int = 0
        self.__wrong_src_code_comments: List[str] = []
        self.__already_added_report_hashes: Set[str] = set()
        self.__new_report_hashes: Set[str] = set()
        self.__all_report_checkers: Set[str] = set()

    @property
    def __manager(self):
        return self.__report_server._manager

    @property
    def __Session(self):
        return self.__report_server._Session

    @property
    def __config_database(self):
        return self.__report_server._config_database

    @property
    def __product(self):
        return self.__report_server._product

    @property
    def __context(self):
        return self.__report_server._context

    @property
    def user_name(self):
        return self.__report_server._get_username()

    def __check_run_limit(self):
        """
        Checks the maximum allowed of uploadable runs for the current product.
        """
        max_run_count = self.__manager.get_max_run_count()

        with DBSession(self.__config_database) as session:
            product = session.query(Product).get(self.__product.id)
            if product.run_limit:
                max_run_count = product.run_limit

        # Session that handles constraints on the run.
        with DBSession(self.__Session) as session:
            if not max_run_count:
                return

            LOG.debug("Check the maximum number of allowed runs which is %d",
                      max_run_count)

            run = session.query(Run) \
                .filter(Run.name == self.__name) \
                .one_or_none()

            # If max_run_count is not set in the config file, it will allow
            # the user to upload unlimited runs.

            run_count = session.query(Run.id).count()

            # If we are not updating a run or the run count is reached the
            # limit it will throw an exception.
            if not run and run_count >= max_run_count:
                remove_run_count = run_count - max_run_count + 1
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                    f"You reached the maximum number of allowed runs "
                    f"({run_count}/{max_run_count})! Please remove at least "
                    f"{remove_run_count} run(s) before you try it again.")

    def __store_run_lock(self, session: DBSession):
        """
        Store a RunLock record for the given run name into the database.
        """
        try:
            # If the run can be stored, we need to lock it first. If there is
            # already a lock in the database for the given run name which is
            # expired and multiple processes are trying to get this entry from
            # the database for update we may get the following exception:
            # could not obtain lock on row in relation "run_locks"
            # This is the reason why we have to wrap this query to a try/except
            # block.
            run_lock = session.query(RunLock) \
                .filter(RunLock.name == self.__name) \
                .with_for_update(nowait=True).one_or_none()
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to get run lock for '%s': %s", self.__name, ex)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                "Someone is already storing to the same run. Please wait "
                "while the other storage is finished and try it again.")

        if not run_lock:
            # If there is no lock record for the given run name, the run
            # is not locked -- create a new lock.
            run_lock = RunLock(self.__name, self.user_name)
            session.add(run_lock)
        elif run_lock.has_expired(
                db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE):
            # There can be a lock in the database, which has already
            # expired. In this case, we assume that the previous operation
            # has failed, and thus, we can re-use the already present lock.
            run_lock.touch()
            run_lock.username = self.user_name
        else:
            # In case the lock exists and it has not expired, we must
            # consider the run a locked one.
            when = run_lock.when_expires(
                db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE)

            username = run_lock.username if run_lock.username is not None \
                else "another user"

            LOG.info("Refusing to store into run '%s' as it is locked by "
                     "%s. Lock will expire at '%s'.", self.__name, username,
                     when)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                "The run named '{0}' is being stored into by {1}. If the "
                "other store operation has failed, this lock will expire "
                "at '{2}'.".format(self.__name, username, when))

        # At any rate, if the lock has been created or updated, commit it
        # into the database.
        try:
            session.commit()
        except (sqlalchemy.exc.IntegrityError,
                sqlalchemy.orm.exc.StaleDataError):
            # The commit of this lock can fail.
            #
            # In case two store ops attempt to lock the same run name at the
            # same time, committing the lock in the transaction that commits
            # later will result in an IntegrityError due to the primary key
            # constraint.
            #
            # In case two store ops attempt to lock the same run name with
            # reuse and one of the operation hangs long enough before COMMIT
            # so that the other operation commits and thus removes the lock
            # record, StaleDataError is raised. In this case, also consider
            # the run locked, as the data changed while the transaction was
            # waiting, as another run wholly completed.

            LOG.info("Run '%s' got locked while current transaction "
                     "tried to acquire a lock. Considering run as locked.",
                     self.__name)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                "The run named '{0}' is being stored into by another "
                "user.".format(self.__name))

    def __free_run_lock(self, session: DBSession):
        """ Remove the lock from the database for the given run name. """
        # Using with_for_update() here so the database (in case it supports
        # this operation) locks the lock record's row from any other access.
        run_lock = session.query(RunLock) \
            .filter(RunLock.name == self.__name) \
            .with_for_update(nowait=True).one()
        session.delete(run_lock)
        session.commit()

    def __store_source_files(
        self,
        source_root: str,
        filename_to_hash: Dict[str, str]
    ) -> Dict[str, int]:
        """ Storing file contents from plist. """

        file_path_to_id = {}

        for file_name, file_hash in filename_to_hash.items():
            source_file_name = os.path.join(source_root, file_name.strip("/"))
            source_file_name = os.path.realpath(source_file_name)
            LOG.debug("Storing source file: %s", source_file_name)
            trimmed_file_path = util.trim_path_prefixes(
                file_name, self.__trim_path_prefixes)

            if not os.path.isfile(source_file_name):
                # The file was not in the ZIP file, because we already
                # have the content. Let's check if we already have a file
                # record in the database or we need to add one.

                LOG.debug('%s not found or already stored.', trimmed_file_path)
                with DBSession(self.__Session) as session:
                    fid = add_file_record(
                        session, trimmed_file_path, file_hash)

                if not fid:
                    LOG.error("File ID for %s is not found in the DB with "
                              "content hash %s. Missing from ZIP?",
                              source_file_name, file_hash)
                file_path_to_id[trimmed_file_path] = fid
                LOG.debug("%d fileid found", fid)
                continue

            with DBSession(self.__Session) as session:
                file_path_to_id[trimmed_file_path] = self.__add_file_content(
                    session, trimmed_file_path, source_file_name, file_hash)

        return file_path_to_id

    def __add_file_content(
        self,
        session: DBSession,
        file_path: str,
        source_file_name: str,
        content_hash: str
    ) -> int:
        """
        Add the necessary file contents. If the file is already stored in the
        database then its ID returns. If content_hash in None then this
        function calculates the content hash. Or if is available at the caller
        and is provided then it will not be calculated again.

        This function must not be called between add_checker_run() and
        finish_checker_run() functions when SQLite database is used!
        add_checker_run() function opens a transaction which is closed by
        finish_checker_run() and since SQLite doesn't support parallel
        transactions, this API call will wait until the other transactions
        finish. In the meantime the run adding transaction times out.
        """

        source_file_content = None
        if not content_hash:
            source_file_content = get_file_content(source_file_name)

            hasher = sha256()
            hasher.update(source_file_content)
            content_hash = hasher.hexdigest()

        file_content = session.query(FileContent).get(content_hash)
        if not file_content:
            if not source_file_content:
                source_file_content = get_file_content(source_file_name)
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
                    File.filepath == file_path) \
            .one_or_none()

        if not file_record:
            try:
                file_record = File(file_path, content_hash)
                session.add(file_record)
                session.commit()
            except sqlalchemy.exc.IntegrityError as ex:
                LOG.error(ex)
                # Other transaction might have added the same file in the
                # meantime.
                session.rollback()
                file_record = session.query(File) \
                    .filter(File.content_hash == content_hash,
                            File.filepath == file_path) \
                    .one_or_none()

        return file_record.id

    def __store_analysis_statistics(
        self,
        session: DBSession,
        run_history_id: int
    ):
        """
        Store analysis statistics for the given run history.

        It will unique the statistics for each analyzer type based on the
        metadata information.
        """
        stats = defaultdict(lambda: {
            "versions": set(),
            "failed_sources": set(),
            "successful_sources": set(),
            "successful": 0
        })

        for mip in self.__mips.values():
            self.__duration += int(sum(mip.check_durations))

            for analyzer_type, res in mip.analyzer_statistics.items():
                if "version" in res:
                    stats[analyzer_type]["versions"].add(res["version"])

                if "failed_sources" in res:
                    if self.__version == '6.9.0':
                        stats[analyzer_type]["failed_sources"].add(
                            'Unavailable in CodeChecker 6.9.0!')
                    else:
                        stats[analyzer_type]["failed_sources"].update(
                            res["failed_sources"])

                if "successful_sources" in res:
                    stats[analyzer_type]["successful_sources"].update(
                        res["successful_sources"])

                if "successful" in res:
                    stats[analyzer_type]["successful"] += res["successful"]

        for analyzer_type, stat in stats.items():
            analyzer_version = None
            if stat["versions"]:
                analyzer_version = zlib.compress(
                    "; ".join(stat["versions"]).encode('utf-8'),
                    zlib.Z_BEST_COMPRESSION)

            failed = 0
            compressed_files = None
            if stat["failed_sources"]:
                compressed_files = zlib.compress(
                    '\n'.join(stat["failed_sources"]).encode('utf-8'),
                    zlib.Z_BEST_COMPRESSION)

                failed = len(stat["failed_sources"])

            successful = len(stat["successful_sources"]) \
                if stat["successful_sources"] else stat["successful"]

            analyzer_statistics = AnalyzerStatistic(
                run_history_id, analyzer_type, analyzer_version,
                successful, failed, compressed_files)

            session.add(analyzer_statistics)

    def __store_analysis_info(
        self,
        session: DBSession,
        run_history: RunHistory
    ):
        """ Store analysis info for the given run history. """
        for src_dir_path, mip in self.__mips.items():
            for analyzer_command in mip.check_commands:
                cmd = zlib.compress(
                    analyzer_command.encode("utf-8"),
                    zlib.Z_BEST_COMPRESSION)

                analysis_info_rows = session \
                    .query(AnalysisInfo) \
                    .filter(AnalysisInfo.analyzer_command == cmd) \
                    .all()

                if analysis_info_rows:
                    # It is possible when multiple runs are stored
                    # simultaneously to the server with the same analysis
                    # command that multiple entries are stored into the
                    # database. In this case we will select the first one.
                    analysis_info = analysis_info_rows[0]
                else:
                    analysis_info = AnalysisInfo(analyzer_command=cmd)
                    session.add(analysis_info)

                run_history.analysis_info.append(analysis_info)
                self.__analysis_info[src_dir_path] = analysis_info

    def __add_checker_run(
        self,
        session: DBSession,
        run_history_time: datetime
    ) -> int:
        """
        Store run related data to the database.
        By default updates the results if name already exists.
        Using the force flag removes existing analysis results for a run.
        """
        try:
            LOG.debug("Adding run '%s'...", self.__name)

            run = session.query(Run) \
                .filter(Run.name == self.__name) \
                .one_or_none()

            if run and self.__force:
                # Clean already collected results.
                if not run.can_delete:
                    # Deletion is already in progress.
                    msg = f"Can't delete {run.id}"
                    LOG.debug(msg)
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                        msg)

                LOG.info('Removing previous analysis results...')
                session.delete(run)
                # Not flushing after delete leads to a constraint violation
                # error later, when adding run entity with the same name as
                # the old one.
                session.flush()

                checker_run = Run(self.__name, self.__version)
                session.add(checker_run)
                session.flush()
                run_id = checker_run.id

            elif run:
                # There is already a run, update the results.
                run.date = datetime.now()
                run.duration = -1
                session.flush()
                run_id = run.id
            else:
                # There is no run create new.
                checker_run = Run(self.__name, self.__version)
                session.add(checker_run)
                session.flush()
                run_id = checker_run.id

            # Add run to the history.
            LOG.debug("Adding run history.")

            if self.__tag is not None:
                run_history = session.query(RunHistory) \
                    .filter(RunHistory.run_id == run_id,
                            RunHistory.version_tag == self.__tag) \
                    .one_or_none()

                if run_history:
                    run_history.version_tag = None
                    session.add(run_history)

            cc_versions = set()
            for mip in self.__mips.values():
                if mip.cc_version:
                    cc_versions.add(mip.cc_version)

            cc_version = '; '.join(cc_versions) if cc_versions else None
            run_history = RunHistory(
                run_id, self.__tag, self.user_name, run_history_time,
                cc_version, self.__description)

            session.add(run_history)
            session.flush()

            LOG.debug("Adding run done.")

            self.__store_analysis_statistics(session, run_history.id)
            self.__store_analysis_info(session, run_history)

            session.flush()
            LOG.debug("Storing analysis statistics done.")

            return run_id
        except Exception as ex:
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    def __add_report(
        self,
        session: DBSession,
        run_id: int,
        file_id: int,
        main_section: MainSection,
        path_events: PathEvents,
        detection_status: str,
        detection_time: datetime,
        analysis_info: AnalysisInfo,
        analyzer_name: Optional[str] = None
    ) -> int:
        """ Add report to the database. """
        def store_bug_events(report_id: int):
            """ Add bug path events. """
            for i, event in enumerate(path_events.events):
                bpe = BugPathEvent(
                    event.startLine, event.startCol, event.endLine,
                    event.endCol, i, event.msg, event.fileId, report_id)
                session.add(bpe)

        def store_bug_path(report_id: int):
            """ Add bug path points. """
            for i, piece in enumerate(path_events.paths):
                brp = BugReportPoint(
                    piece.startLine, piece.startCol, piece.endLine,
                    piece.endCol, i, piece.fileId, report_id)
                session.add(brp)

        def store_extended_bug_data(report_id: int):
            """ Add extended bug data objects to the database session. """
            for data in path_events.extended_data:
                data_type = report_extended_data_type_str(data.type)
                red = ExtendedReportData(
                    data.startLine, data.startCol, data.endLine, data.endCol,
                    data.message, data.fileId, report_id, data_type)
                session.add(red)

        try:
            checker_name = main_section['check_name']
            severity_name = self.__context.severity_map.get(checker_name)
            severity = ttypes.Severity._NAMES_TO_VALUES[severity_name]
            report = Report(
                run_id, main_section['issue_hash_content_of_line_in_context'],
                file_id, main_section['description'],
                checker_name or 'NOT FOUND',
                main_section['category'], main_section['type'],
                main_section['location']['line'],
                main_section['location']['col'],
                severity, detection_status, detection_time,
                len(path_events.events), analyzer_name)

            session.add(report)
            session.flush()

            LOG.debug("storing bug path")
            store_bug_path(report.id)

            LOG.debug("storing events")
            store_bug_events(report.id)

            LOG.debug("storing extended report data")
            store_extended_bug_data(report.id)

            if analysis_info:
                report.analysis_info.append(analysis_info)

            return report.id

        except Exception as ex:
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    def __process_report_file(
        self,
        report_file_path: str,
        session: DBSession,
        source_root: str,
        run_id: int,
        file_path_to_id: Dict[str, int],
        run_history_time: datetime,
        skip_handler: skiplist_handler.SkipListHandler,
        hash_map_reports: Dict[str, List[Any]]
    ) -> bool:
        """
        Process and save reports from the given report file to the database.
        """
        try:
            files, reports = plist_parser.parse_plist_file(report_file_path)
        except Exception as ex:
            LOG.warning('Parsing the plist failed: %s', str(ex))
            return False

        if not reports:
            return True

        trimmed_files = {}
        file_ids = {}
        missing_ids_for_files = []

        for k, v in files.items():
            trimmed_files[k] = \
                util.trim_path_prefixes(v, self.__trim_path_prefixes)

        for file_name in trimmed_files.values():
            file_id = file_path_to_id.get(file_name, -1)
            if file_id == -1:
                missing_ids_for_files.append(file_name)
                continue

            file_ids[file_name] = file_id

        if missing_ids_for_files:
            LOG.warning("Failed to get file path id for '%s'!",
                        ' '.join(missing_ids_for_files))
            return False

        def set_review_status(report: ReportType):
            """
            Set review status for the given report if there is any source code
            comment.
            """
            checker_name = report.main['check_name']
            last_report_event = report.bug_path[-1]

            # The original file path is needed here not the trimmed
            # because the source files are extracted as the original
            # file path.
            file_name = files[last_report_event['location']['file']]

            source_file_name = os.path.realpath(
                os.path.join(source_root, file_name.strip("/")))

            # Check and store source code comments.
            if not os.path.isfile(source_file_name):
                return

            report_line = last_report_event['location']['line']
            source_file = os.path.basename(file_name)

            src_comment_data = parse_codechecker_review_comment(
                source_file_name, report_line, checker_name)

            if len(src_comment_data) == 1:
                status = src_comment_data[0]['status']
                rw_status = ttypes.ReviewStatus.FALSE_POSITIVE
                if status == 'confirmed':
                    rw_status = ttypes.ReviewStatus.CONFIRMED
                elif status == 'intentional':
                    rw_status = ttypes.ReviewStatus.INTENTIONAL

                self.__report_server._setReviewStatus(
                    session, report.report_hash, rw_status,
                    src_comment_data[0]['message'], run_history_time)
            elif len(src_comment_data) > 1:
                LOG.warning(
                    "Multiple source code comment can be found "
                    "for '%s' checker in '%s' at line %s. "
                    "This bug will not be suppressed!",
                    checker_name, source_file, report_line)

                self.__wrong_src_code_comments.append(
                    f"{source_file}|{report_line}|{checker_name}")

        root_dir_path = os.path.dirname(report_file_path)
        mip = self.__mips[root_dir_path]
        analysis_info = self.__analysis_info.get(root_dir_path)

        for report in reports:
            self.__all_report_checkers.add(report.check_name)

            if skip_handler.should_skip(report.file_path):
                continue

            report.trim_path_prefixes(self.__trim_path_prefixes)

            report_path_hash = get_report_path_hash(report)
            if report_path_hash in self.__already_added_report_hashes:
                LOG.debug('Not storing report. Already added: %s', report)
                continue

            LOG.debug("Storing report to the database...")

            bug_id = report.report_hash

            detection_status = 'new'
            detected_at = run_history_time

            if bug_id in hash_map_reports:
                old_report = hash_map_reports[bug_id][0]
                old_status = old_report.detection_status
                detection_status = 'reopened' \
                    if old_status == 'resolved' else 'unresolved'
                detected_at = old_report.detected_at

            analyzer_name = get_analyzer_name(
                report.check_name, mip.checker_to_analyzer, report.metadata)

            path_events = collect_paths_events(report, file_ids, trimmed_files)

            report_id = self.__add_report(
                session, run_id, file_ids[report.file_path], report.main,
                path_events, detection_status, detected_at, analysis_info,
                analyzer_name)

            self.__new_report_hashes.add(bug_id)
            self.__already_added_report_hashes.add(report_path_hash)

            set_review_status(report)

            LOG.debug("Storing report done. ID=%d", report_id)

        return True

    def __store_reports(
        self,
        session: DBSession,
        report_dir: str,
        source_root: str,
        run_id: int,
        file_path_to_id: Dict[str, int],
        run_history_time: datetime
    ):
        """ Parse up and store the plist report files. """
        def get_skip_handler(
            report_dir: str
        ) -> skiplist_handler.SkipListHandler:
            """ Get a skip list handler based on the given report directory."""
            skip_file_path = os.path.join(report_dir, 'skip_file')
            if not os.path.exists(skip_file_path):
                return skiplist_handler.SkipListHandler()

            LOG.debug("Pocessing skip file %s", skip_file_path)
            try:
                with open(skip_file_path,
                          encoding="utf-8", errors="ignore") as f:
                    skip_content = f.read()
                    LOG.debug(skip_content)

                    return skiplist_handler.SkipListHandler(skip_content)
            except (IOError, OSError) as err:
                LOG.error("Failed to open skip file: %s", err)
                raise

        # Reset internal data.
        self.__already_added_report_hashes = set()
        self.__new_report_hashes = set()
        self.__all_report_checkers = set()

        all_reports = session.query(Report) \
            .filter(Report.run_id == run_id) \
            .all()

        hash_map_reports = defaultdict(list)
        for report in all_reports:
            hash_map_reports[report.bug_id].append(report)

        enabled_checkers: Set[str] = set()
        disabled_checkers: Set[str] = set()

        # Processing PList files.
        for root_dir_path, _, report_file_paths in os.walk(report_dir):
            LOG.debug("Get reports from '%s' directory", root_dir_path)

            skip_handler = get_skip_handler(root_dir_path)

            mip = self.__mips[root_dir_path]
            enabled_checkers.update(mip.enabled_checkers)
            disabled_checkers.update(mip.disabled_checkers)

            for f in report_file_paths:
                if not f.endswith('.plist'):
                    continue

                LOG.debug("Parsing input file '%s'", f)

                report_file_path = os.path.join(root_dir_path, f)
                self.__process_report_file(
                    report_file_path, session, source_root, run_id,
                    file_path_to_id, run_history_time,
                    skip_handler, hash_map_reports)

        # If a checker was found in a plist file it can not be disabled so we
        # will add this to the enabled checkers list and remove this checker
        # from the disabled checkers list.
        # Also if multiple report directories are stored and a checker was
        # enabled in one report directory but it was disabled in another
        # directory we will mark this checker as enabled.
        enabled_checkers |= self.__all_report_checkers
        disabled_checkers -= self.__all_report_checkers

        reports_to_delete = set()
        for bug_hash, reports in hash_map_reports.items():
            if bug_hash in self.__new_report_hashes:
                reports_to_delete.update([x.id for x in reports])
            else:
                for report in reports:
                    # We set the fix date of a report only if the report
                    # has not been fixed before.
                    if report.fixed_at:
                        continue

                    checker = report.checker_id
                    if checker in disabled_checkers:
                        report.detection_status = 'off'
                    elif checker_is_unavailable(checker, enabled_checkers):
                        report.detection_status = 'unavailable'
                    else:
                        report.detection_status = 'resolved'

                    report.fixed_at = run_history_time

        if reports_to_delete:
            self.__report_server._removeReports(
                session, list(reports_to_delete))

    def finish_checker_run(
        self,
        session: DBSession,
        run_id: int
    ) -> bool:
        """ Finish the storage of the given run. """
        try:
            LOG.debug("Finishing checker run")
            run = session.query(Run).get(run_id)
            if not run:
                return False

            run.mark_finished()
            run.duration = self.__duration

            return True
        except Exception as ex:
            LOG.error(ex)

        return False

    def store(self) -> int:
        """ Store run results to the server. """
        start_time = time.time()

        # Check constraints of the run.
        self.__check_run_limit()

        with DBSession(self.__Session) as session:
            self.__store_run_lock(session)

        try:
            with TemporaryDirectory(
                dir=self.__context.codechecker_workspace
            ) as zip_dir:
                LOG.info("[%s] Unzip storage file...", self.__name)
                zip_size = unzip(self.__b64zip, zip_dir)
                LOG.info("[%s] Unzip storage file done.", self.__name)

                if zip_size == 0:
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.
                        ErrorCode.GENERAL,
                        "The received zip file content is empty!")

                LOG.debug("Using unzipped folder '%s'", zip_dir)

                source_root = os.path.join(zip_dir, 'root')
                report_dir = os.path.join(zip_dir, 'reports')
                content_hash_file = os.path.join(
                    zip_dir, 'content_hashes.json')

                filename_to_hash = \
                    util.load_json_or_empty(content_hash_file, {})

                LOG.info("[%s] Store source files...", self.__name)
                file_path_to_id = self.__store_source_files(
                    source_root, filename_to_hash)
                LOG.info("[%s] Store source files done.", self.__name)

                run_history_time = datetime.now()

                # Parse all metadata information from the report directory.
                for root_dir_path, _, _ in os.walk(report_dir):
                    metadata_file_path = os.path.join(
                        root_dir_path, 'metadata.json')

                    self.__mips[root_dir_path] = \
                        MetadataInfoParser(metadata_file_path)

                # When we use multiple server instances and we try to run
                # multiple storage to each server which contain at least two
                # reports which have the same report hash and have source code
                # comments it is possible that the following exception will be
                # thrown: (psycopg2.extensions.TransactionRollbackError)
                # deadlock detected.
                # The problem is that the report hash is the key for the
                # review data table and both of the store actions try to
                # update the same review data row.
                # Neither of the two processes can continue, and they will wait
                # for each other indefinitely. PostgreSQL in this case will
                # terminate one transaction with the above exception.
                # For this reason in case of failure we will wait some seconds
                # and try to run the storage again.
                # For more information see #2655 and #2653 issues on github.
                max_num_of_tries = 3
                num_of_tries = 0
                sec_to_wait_after_failure = 60
                while True:
                    try:
                        # This session's transaction buffer stores the actual
                        # run data into the database.
                        with DBSession(self.__Session) as session:
                            # Load the lock record for "FOR UPDATE" so that the
                            # transaction that handles the run's store
                            # operations has a lock on the database row itself.
                            run_lock = session.query(RunLock) \
                                .filter(RunLock.name == self.__name) \
                                .with_for_update(nowait=True).one()

                            # Do not remove this seemingly dummy print, we need
                            # to make sure that the execution of the SQL
                            # statement is not optimised away and the fetched
                            # row is not garbage collected.
                            LOG.debug("Storing into run '%s' locked at '%s'.",
                                      self.__name, run_lock.locked_at)

                            # Actual store operation begins here.
                            run_id = self.__add_checker_run(
                                session, run_history_time)

                            LOG.info("[%s] Store reports...", self.__name)
                            self.__store_reports(
                                session, report_dir, source_root, run_id,
                                file_path_to_id, run_history_time)
                            LOG.info("[%s] Store reports done.", self.__name)

                            self.finish_checker_run(session, run_id)

                            session.commit()

                            LOG.info("'%s' stored results (%s KB "
                                     "/decompressed/) to run '%s' (id: %d) in "
                                     "%s seconds.", self.user_name,
                                     round(zip_size / 1024),
                                     self.__name, run_id,
                                     round(time.time() - start_time, 2))

                            return run_id
                    except (sqlalchemy.exc.OperationalError,
                            sqlalchemy.exc.ProgrammingError) as ex:
                        num_of_tries += 1

                        if num_of_tries == max_num_of_tries:
                            raise codechecker_api_shared.ttypes.RequestFailed(
                                codechecker_api_shared.ttypes.
                                ErrorCode.DATABASE,
                                "Storing reports to the database failed: "
                                "{0}".format(ex))

                        LOG.error("Storing reports of '%s' run failed: "
                                  "%s.\nWaiting %d sec before trying to store "
                                  "it again!", self.__name, ex,
                                  sec_to_wait_after_failure)
                        time.sleep(sec_to_wait_after_failure)
                        sec_to_wait_after_failure *= 2
        except Exception as ex:
            LOG.error("Failed to store results: %s", ex)
            import traceback
            traceback.print_exc()
            raise
        finally:
            # In any case if the "try" block's execution began, a run lock must
            # exist, which can now be removed, as storage either completed
            # successfully, or failed in a detectable manner.
            # (If the failure is undetectable, the coded grace period expiry
            # of the lock will allow further store operations to the given
            # run name.)
            with DBSession(self.__Session) as session:
                self.__free_run_lock(session)

            if self.__wrong_src_code_comments:
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.SOURCE_FILE,
                    "Multiple source code comment can be found with the same "
                    "checker name for same bug!",
                    self.__wrong_src_code_comments)
