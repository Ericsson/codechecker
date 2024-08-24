# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Implementation of the ``massStoreRunAsynchronous()`` API function that store
run data to a product's report database.

Called via `report_server`, but factored out here for readability.
"""
import base64
from collections import defaultdict
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlalchemy
import tempfile
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast
import zipfile
import zlib

from codechecker_api_shared.ttypes import DBStatus, ErrorCode, RequestFailed
from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from codechecker_common import skiplist_handler
from codechecker_common.logger import get_logger
from codechecker_common.review_status_handler import ReviewStatusHandler, \
    SourceReviewStatus
from codechecker_common.util import format_size, load_json, path_for_fake_root

from codechecker_report_converter import twodim
from codechecker_report_converter.util import trim_path_prefixes
from codechecker_report_converter.report import \
    FakeChecker, Report, UnknownChecker, report_file
from codechecker_report_converter.report.hash import get_report_path_hash

from ..database import db_cleanup
from ..database.config_db_model import Product
from ..database.database import DBSession
from ..database.run_db_model import \
    AnalysisInfo, AnalysisInfoChecker, AnalyzerStatistic, \
    BugPathEvent, BugReportPoint, \
    Checker, \
    ExtendedReportData, \
    File, FileContent, \
    Report as DBReport, ReportAnnotations, ReviewStatus as ReviewStatusRule, \
    Run, RunLock as DBRunLock, RunHistory
from ..metadata import checker_is_unavailable, MetadataInfoParser

from .report_annotations import report_annotation_types
from ..product import Product as ServerProduct
from ..session_manager import SessionManager
from ..task_executors.abstract_task import AbstractTask
from ..task_executors.task_manager import TaskManager
from .thrift_enum_helper import report_extended_data_type_str


LOG = get_logger('server')
STORE_TIME_LOG = get_logger('store_time')


class StepLog:
    """
    Simple context manager that logs an arbitrary step's comment and time
    taken annotated with a run name.
    """

    def __init__(self, run_name: str, message: str):
        self._run_name = run_name
        self._msg = message
        self._start_time = time.time()

    def __enter__(self, *_args):
        LOG.info("[%s] %s...", self._run_name, self._msg)

    def __exit__(self, *_args):
        LOG.info("[%s] %s. Done. (Duration: %.2f sec)",
                 self._run_name, self._msg, time.time() - self._start_time)


class RunLock:
    def __init__(self, session: DBSession, run_name: str):
        self.__session = session
        self.__run_name = run_name
        self.__run_lock = None

    def __enter__(self, *_args):
        # Load the lock record for "FOR UPDATE" so that the transaction that
        # handles the run's store operations has a lock on the database row
        # itself.
        self.__run_lock = self.__session.query(DBRunLock) \
            .filter(DBRunLock.name == self.__run_name) \
            .with_for_update(nowait=True) \
            .one()

        # Do *NOT* remove this seemingly dummy print. The query functions on
        # result in a **proxy** object, essentially a weak pointer, without(!)
        # the execution of any underlying SQL statements. Which means that
        # without the evaluation of the member of this query (with the
        # . operator) there would be no actual DBMS-level lock in place.
        # (Not having debug logs enabled is not a problem: the evaluation of
        # the arguments still take place even if the logging configuration
        # prevents the actual printing of the log line.)
        LOG.debug("Acquired exclusive lock for run '%s' that was originally "
                  "locked at '%s'.",
                  self.__run_name, self.__run_lock.locked_at)
        return self

    def __exit__(self, *_args):
        self.__run_lock = None
        self.__session = None

    def store_run_lock_in_db(self, associated_user: str):
        """
        Stores a `DBRunLock` record for the given run name into the database.
        """
        try:
            # If the run can be stored, we need to lock it first. If there is
            # already a lock in the database for the given run name which is
            # expired and multiple processes are trying to get this entry from
            # the database for update we may get the following exception:
            # could not obtain lock on row in relation "run_locks"
            # This is the reason why we have to wrap this query to a try/except
            # block.
            run_lock: Optional[DBRunLock] = self.__session.query(DBRunLock) \
                .filter(DBRunLock.name == self.__run_name) \
                .with_for_update(nowait=True) \
                .one_or_none()
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to get run lock for '%s': %s",
                      self.__run_name, ex)
            raise RequestFailed(
                ErrorCode.DATABASE,
                "Someone is already storing to the same run. Please wait "
                "while the other storage is finished and try it again.") \
                from ex

        if not run_lock:
            # If there is no lock record for the given run name, the run
            # is not locked -> create a new lock.
            self.__session.add(DBRunLock(self.__run_name, associated_user))
            LOG.debug("Acquiring 'run_lock' for '%s' on run '%s' ...",
                      associated_user, self.__run_name)
        elif run_lock.has_expired(
                db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE):
            # There can be a lock in the database, which has already
            # expired. In this case, we assume that the previous operation
            # has failed, and thus, we can re-use the already present lock.
            run_lock.touch()
            run_lock.username = associated_user
            LOG.debug("Reusing existing, stale 'run_lock' record on "
                      "run '%s' ...",
                      self.__run_name)
        else:
            # In case the lock exists and it has not expired, we must
            # consider the run a locked one.
            when = run_lock.when_expires(
                db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE)
            username = run_lock.username or "another user"
            LOG.info("Refusing to store into run '%s' as it is locked by "
                     "%s. Lock will expire at '%s'.",
                     self.__run_name, username, when)
            raise RequestFailed(
                ErrorCode.DATABASE,
                f"The run named '{self.__run_name}' is being stored into by "
                f"{username}. If the other store operation has failed, this "
                f"lock will expire at '{when}'.")

        # At any rate, if the lock has been created or updated, commit it
        # into the database.
        try:
            self.__session.commit()
        except (sqlalchemy.exc.IntegrityError,
                sqlalchemy.orm.exc.StaleDataError) as ex:
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
                     self.__run_name)
            raise RequestFailed(
                ErrorCode.DATABASE,
                f"The run named '{self.__run_name}' is being stored into by "
                "another user.") from ex

        LOG.debug("Successfully acquired 'run_lock' for '%s' on run '%s'.",
                  associated_user, self.__run_name)

    def drop_run_lock_from_db(self):
        """Remove the run_lock row from the database for the current run."""
        # Using with_for_update() here so the database (in case it supports
        # this operation) locks the lock record's row from any other access.
        LOG.debug("Releasing 'run_lock' from run '%s' ...")
        run_lock: Optional[DBRunLock] = self.__session.query(DBRunLock) \
            .filter(DBRunLock.name == self.__run_name) \
            .with_for_update(nowait=True).one()
        if not run_lock:
            raise KeyError(
                f"No 'run_lock' in database for run '{self.__run_name}'")
        locked_at = run_lock.locked_at
        username = run_lock.username

        self.__session.delete(run_lock)
        self.__session.commit()

        LOG.debug("Released 'run_lock' (originally acquired by '%s' on '%s') "
                  "from run '%s'.",
                  username, str(locked_at), self.__run_name)


def unzip(run_name: str, b64zip: str, output_dir: Path) -> int:
    """
    This function unzips a Base64 encoded and ZLib-compressed ZIP file.
    This ZIP is extracted to a temporary directory and the ZIP is then deleted.
    The function returns the size of the extracted decompressed ZIP file.
    """
    if not b64zip:
        return 0

    with tempfile.NamedTemporaryFile(
            suffix=".zip", dir=output_dir) as zip_file:
        LOG.debug("Decompressing input massStoreRun() ZIP to '%s' ...",
                  zip_file.name)
        start_time = time.time()
        zip_file.write(zlib.decompress(base64.b64decode(b64zip)))
        zip_file.flush()
        end_time = time.time()

        size = os.stat(zip_file.name).st_size
        LOG.debug("Decompressed input massStoreRun() ZIP '%s' -> '%s' "
                  "(compression ratio: %.2f%%) in '%s'.",
                  format_size(len(b64zip)), format_size(size),
                  (size / len(b64zip)),
                  timedelta(seconds=end_time - start_time))

        with StepLog(run_name, "Extract massStoreRun() ZIP contents"), \
                zipfile.ZipFile(zip_file, 'r', allowZip64=True) as zip_handle:
            LOG.debug("Extracting massStoreRun() ZIP '%s' to '%s' ...",
                      zip_file.name, output_dir)
            try:
                zip_handle.extractall(output_dir)
                return size
            except Exception:
                LOG.error("Failed to extract received ZIP.")
                import traceback
                traceback.print_exc()
                raise


def get_file_content(file_path: str) -> bytes:
    """Return the file content for the given `file_path`."""
    with open(file_path, 'rb') as f:
        return f.read()


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

    This function doesn't insert blame info in the File objects because those
    are added by __add_blame_info(). In previous CodeChecker versions git info
    was not stored at all, so upgrading to a new CodeChecker results the
    storage of git blame info even for files that are already stored. For this
    reason we can't avoid an update on File and FileContent tables, but we can
    avoid double reading of blame info json files.
    """
    file_record = session.query(File) \
        .filter(File.content_hash == content_hash,
                File.filepath == file_path) \
        .one_or_none()

    if file_record:
        return file_record.id

    try:
        # Parallel storage of runs containing common file paths results a
        # "duplicate key violation" error. This is handled by CodeChecker, so
        # practically it causes no problem. The INSERT command of the second
        # transaction will be thrown away. However, some DB systems are
        # supporting "ON CONFLICT DO NOTHING" clause in INSERT statement which
        # solves the same issue gracefully.
        # TODO: "ON CONFLICT DO NOTHING" feature is available for SQLite engine
        # too in SQLAlchemy 1.4.
        if session.bind.dialect.name == 'postgresql':
            insert_stmt = sqlalchemy.dialects.postgresql.insert(File).values(
                filepath=file_path,
                filename=os.path.basename(file_path),
                content_hash=content_hash).on_conflict_do_nothing(
                    index_elements=['filepath', 'content_hash'])
            file_id = session.execute(insert_stmt).inserted_primary_key[0]
            session.commit()
            return file_id

        file_record = File(file_path, content_hash, None, None)
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


def get_blame_file_data(
    blame_file: Path
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get blame information from the given file.

    It will return a tuple of 'blame information', 'remote url' and
    'tracking branch'.
    """
    blame_info = None
    remote_url = None
    tracking_branch = None

    if blame_file.is_file():
        data = load_json(blame_file)
        if data:
            remote_url = data.get("remote_url")
            tracking_branch = data.get("tracking_branch")

            blame_info = data

            # Remove fields which are not needed anymore from the blame info.
            del blame_info["remote_url"]
            del blame_info["tracking_branch"]

    return blame_info, remote_url, tracking_branch


def checker_name_for_report(report: Report) -> Tuple[str, str]:
    return (report.analyzer_name or UnknownChecker[0],
            report.checker_name or UnknownChecker[1])


class MassStoreRunInputHandler:
    """Prepares a `MassStoreRunTask` from an API input."""

    # Note: The implementation of this class is executed in the "foreground",
    # in the context of an API handler process!
    # **DO NOT** put complex logic here that would take too much time to
    # validate.
    # Long-running actions of a storage process should be in
    # MassStoreRunImplementation instead!

    def __init__(self,
                 session_manager: SessionManager,
                 config_db_sessionmaker,
                 product_db_sessionmaker,
                 task_manager: TaskManager,
                 package_context,
                 product_id: int,
                 run_name: str,
                 run_description: Optional[str],
                 store_tag: Optional[str],
                 client_version: str,
                 force_overwrite_of_run: bool,
                 path_prefixes_to_trim: Optional[List[str]],
                 zipfile_contents_base64: str,
                 user_name: str):
        self._input_handling_start_time = time.time()
        self._session_manager = session_manager
        self._config_db = config_db_sessionmaker
        self._product_db = product_db_sessionmaker
        self._tm = task_manager
        self._package_context = package_context
        self._input_zip_blob = zipfile_contents_base64
        self.client_version = client_version
        self.force_overwrite_of_run = force_overwrite_of_run
        self.path_prefixes_to_trim = path_prefixes_to_trim
        self.run_name = run_name
        self.run_description = run_description
        self.store_tag = store_tag
        self.user_name = user_name

        with DBSession(self._config_db) as session:
            product: Optional[Product] = session.query(Product) \
                .get(product_id)
            if not product:
                raise KeyError(f"No product with ID '{product_id}'")

            self._product = product

    def check_store_input_validity_at_face_value(self):
        """
        Performs semantic checks of a ``massStoreRunAsynchronous()`` Thrift
        call that can be done with trivial amounts of work (i.e., without
        actually parsing the full input ZIP).
        """
        self._check_run_limit()
        self._store_run_lock()  # Fails if the run can not be stored into.

    def create_mass_store_task(self,
                               is_actually_asynchronous=False) \
            -> "MassStoreRunTask":
        """
        Constructs the `MassStoreRunTask` for the handled and verified input.

        Calling this function results in observable changes outside the
        process's memory, as it records the task into the database and
        extracts things to the server's storage area.
        """
        token = self._tm.allocate_task_record(
            "report_server::massStoreRunAsynchronous()"
            if is_actually_asynchronous
            else "report_server::massStoreRun()",
            ("Legacy s" if not is_actually_asynchronous else "S") +
            f"tore of results to '{self._product.endpoint}' - "
            f"'{self.run_name}'",
            self.user_name,
            self._product)
        temp_dir = self._tm.create_task_data(token)
        extract_dir = temp_dir / "store_zip"
        os.makedirs(extract_dir, exist_ok=True)

        try:
            with StepLog(self.run_name,
                         "Save massStoreRun() ZIP data to server storage"):
                zip_size = unzip(self.run_name,
                                 self._input_zip_blob,
                                 extract_dir)

                if not zip_size:
                    raise RequestFailed(ErrorCode.GENERAL,
                                        "The uploaded ZIP file is empty!")
        except Exception:
            LOG.error("Failed to extract massStoreRunAsynchronous() ZIP!")
            import traceback
            traceback.print_exc()
            raise

        self._input_handling_end_time = time.time()

        try:
            with open(temp_dir / "store_configuration.json", 'w',
                      encoding="utf-8") as cfg_f:
                json.dump({
                    "client_version": self.client_version,
                    "force_overwrite": self.force_overwrite_of_run,
                    "path_prefixes_to_trim": self.path_prefixes_to_trim,
                    "run_name": self.run_name,
                    "run_description": self.run_description,
                    "store_tag": self.store_tag,
                    "user_name": self.user_name,
                    }, cfg_f)
        except Exception:
            LOG.error("Failed to write massStoreRunAsynchronous() "
                      "configuration!")
            import traceback
            traceback.print_exc()
            raise

        task = MassStoreRunTask(token, temp_dir,
                                self._package_context,
                                self._product.id,
                                zip_size,
                                self._input_handling_end_time -
                                self._input_handling_start_time)

        if not is_actually_asynchronous:
            self._tm.add_comment(
                task,
                "WARNING!\nExecuting a legacy 'massStoreRun()' API call!",
                "SYSTEM")

        return task

    def _check_run_limit(self):
        """
        Checks the maximum allowed number of uploadable runs for the current
        product.
        """
        run_limit: Optional[int] = self._session_manager.get_max_run_count()
        if self._product.run_limit:
            run_limit = self._product.run_limit

        if not run_limit:
            # Allowing the user to upload an unlimited number of runs.
            return
        LOG.debug("Checking the maximum number of allowed runs in '%s', "
                  "which is %d.",
                  self._product.endpoint, run_limit)

        with DBSession(self._product_db) as session:
            existing_run: Optional[Run] = session.query(Run) \
                .filter(Run.name == self.run_name) \
                .one_or_none()
            run_count = session.query(Run.id).count()

        if not existing_run and run_count >= run_limit:
            raise RequestFailed(
                ErrorCode.GENERAL,
                "You reached the maximum number of allowed runs "
                f"({run_count}/{run_limit})! "
                f"Please remove at least {run_count - run_limit + 1} "
                "run(s) before you try again!")

    def _store_run_lock(self):
        """Commits a `DBRunLock` for the to-be-stored `Run`, if available."""
        with DBSession(self._product_db) as session:
            RunLock(session, self.run_name) \
                .store_run_lock_in_db(self.user_name)


class MassStoreRunTask(AbstractTask):
    """Executes `MassStoreRun` as a background job."""

    def __init__(self, token: str, data_path: Path,
                 package_context,
                 product_id: int,
                 input_zip_size: int,
                 preparation_time_elapsed: float):
        """
        Creates the `AbstractTask` implementation for
        ``massStoreRunAsynchronous()``.

        `preparation_time_elapsed` records how much time was spent by the
        input handling that prepared the task.
        This time will be added to the total time spent processing the results
        in the background.
        (The time spent in waiting between task enschedulement and task
        execution is not part of the total time.)
        """
        super().__init__(token, data_path)
        self._package_context = package_context
        self._product_id = product_id
        self.input_zip_size = input_zip_size
        self.time_spent_on_task_preparation = preparation_time_elapsed

    def _implementation(self, tm: TaskManager):
        try:
            with open(self.data_path / "store_configuration.json", 'r',
                      encoding="utf-8") as cfg_f:
                self.store_configuration = json.load(cfg_f)
        except Exception:
            LOG.error("Invalid or unusable massStoreRunAsynchronous() "
                      "configuration!")
            raise

        with DBSession(tm.configuration_database_session_factory) as session:
            db_product: Optional[Product] = session.query(Product) \
                .get(self._product_id)
            if not db_product:
                raise KeyError(f"No product with ID '{self._product_id}'")

            self._product = ServerProduct(db_product.id,
                                          db_product.endpoint,
                                          db_product.display_name,
                                          db_product.connection,
                                          self._package_context,
                                          tm.environment)

        self._product.connect()
        if self._product.db_status != DBStatus.OK:
            raise EnvironmentError("Database for product "
                                   f"'{self._product.endpoint}' is in "
                                   "a bad shape!")

        m = MassStoreRun(self.data_path / "store_zip",
                         self._package_context,
                         tm.configuration_database_session_factory,
                         self._product,
                         self.store_configuration["run_name"],
                         self.store_configuration["store_tag"],
                         self.store_configuration["client_version"],
                         self.store_configuration["force_overwrite"],
                         self.store_configuration["path_prefixes_to_trim"],
                         self.store_configuration["run_description"],
                         self.store_configuration["user_name"],
                         )
        m.store(self.input_zip_size, self.time_spent_on_task_preparation)


class MassStoreRun:
    """Implementation for ``massStoreRunAsynchronous()``."""

    # Note: The implementation of this class is called from MassStoreRunTask
    # and it is executed in the background, in the context of a Task worker
    # process.
    # This is the place where complex implementation logic must go, but be
    # careful, there is no way to communicate with the user's client anymore!

    # TODO: Poll the task manager at regular points for a cancel signal!

    def __init__(self,
                 zip_dir: Path,
                 package_context,
                 config_db,
                 product: ServerProduct,
                 name: str,
                 tag: Optional[str],
                 version: Optional[str],
                 force: bool,
                 trim_path_prefix_list: Optional[List[str]],
                 description: Optional[str],
                 user_name: str,
                 ):
        self._zip_dir = zip_dir
        self._name = name
        self._tag = tag
        self._version = version
        self._force = force
        self._trim_path_prefixes = trim_path_prefix_list
        self._description = description
        self._user_name = user_name
        self.__config_db = config_db
        self.__package_context = package_context
        self.__product = product

        self.__mips: Dict[str, MetadataInfoParser] = {}
        self.__analysis_info: Dict[str, AnalysisInfo] = {}
        self.__checker_row_cache: Dict[Tuple[str, str], Checker] = {}
        self.__duration: int = 0
        self.__report_count: int = 0
        self.__report_limit: int = 0
        self.__wrong_src_code_comments: List[str] = []
        self.__already_added_report_hashes: Set[str] = set()
        self.__new_report_hashes: Dict[str, Tuple] = {}
        self.__all_report_checkers: Set[str] = set()
        self.__added_reports: List[Tuple[DBReport, Report]] = []
        self.__reports_with_fake_checkers: Dict[
            # Either a DBReport *without* an ID, or the ID of a committed
            # DBReport.
            str, Tuple[Report, Union[DBReport, int]]] = {}

        with DBSession(config_db) as session:
            product = session.query(Product).get(self.__product.id)
            self.__report_limit = product.report_limit

    def __store_source_files(
        self,
        source_root: Path,
        filename_to_hash: Dict[str, str]
    ) -> Dict[str, int]:
        """ Storing file contents from plist. """

        file_path_to_id = {}

        for file_name, file_hash in filename_to_hash.items():
            source_file_path = path_for_fake_root(file_name, str(source_root))
            LOG.debug("Storing source file: %s", source_file_path)
            trimmed_file_path = trim_path_prefixes(
                file_name, self._trim_path_prefixes)

            if not os.path.isfile(source_file_path):
                # The file was not in the ZIP file, because we already
                # have the content. Let's check if we already have a file
                # record in the database or we need to add one.

                LOG.debug('%s not found or already stored.', trimmed_file_path)
                with DBSession(self.__product.session_factory) as session:
                    fid = add_file_record(
                        session, trimmed_file_path, file_hash)

                if fid:
                    file_path_to_id[trimmed_file_path] = fid
                    LOG.debug("%d fileid found", fid)
                else:
                    LOG.error("File ID for %s is not found in the DB with "
                              "content hash %s. Missing from ZIP?",
                              source_file_path, file_hash)
                continue

            with DBSession(self.__product.session_factory) as session:
                self.__add_file_content(session, source_file_path, file_hash)

                file_path_to_id[trimmed_file_path] = add_file_record(
                    session, trimmed_file_path, file_hash)

        return file_path_to_id

    def __add_blame_info(
        self,
        blame_root: Path,
        filename_to_hash: Dict[str, str]
    ):
        """
        This function updates blame info in File and FileContent tables if
        these were NULL. This function exists only because in earlier
        CodeChecker versions blame info was not stored in these tables and
        in a subsequent storage we can't update the tables for an unchanged
        file since __store_source_files() updates only the ones that are in the
        .zip file. This function stores blame info even if the corresponding
        source file is not in the .zip file.
        """
        with DBSession(self.__product.session_factory) as session:
            for subdir, _, files in os.walk(blame_root):
                for f in files:
                    blame_file = Path(subdir) / f
                    file_path = f"/{str(blame_file.relative_to(blame_root))}"
                    blame_info, remote_url, tracking_branch = \
                        get_blame_file_data(blame_file)

                    compressed_blame_info = None
                    if blame_info:
                        compressed_blame_info = zlib.compress(
                            json.dumps(blame_info).encode('utf-8'),
                            zlib.Z_BEST_COMPRESSION)

                    session \
                        .query(FileContent) \
                        .filter(FileContent.blame_info.is_(None)) \
                        .filter(FileContent.content_hash ==
                                filename_to_hash.get(file_path)) \
                        .update({"blame_info": compressed_blame_info})

                    session \
                        .query(File) \
                        .filter(File.remote_url.is_(None)) \
                        .filter(File.filepath == file_path) \
                        .update({
                            "remote_url": remote_url,
                            "tracking_branch": tracking_branch})

            session.commit()

    def __add_file_content(
        self,
        session: DBSession,
        source_file_name: str,
        content_hash: Optional[str]
    ):
        """
        Add the necessary file contents. If content_hash in None then this
        function calculates the content hash. Or if it's available at the
        caller and it's provided then it will not be calculated again.

        This function must not be called between add_checker_run() and
        finish_checker_run() functions when SQLite database is used!
        add_checker_run() function opens a transaction which is closed by
        finish_checker_run() and since SQLite doesn't support parallel
        transactions, this API call will wait until the other transactions
        finish. In the meantime the run adding transaction times out.

        This function doesn't insert blame info in the FileContent objects
        because those are added by __add_blame_info(). In previous CodeChecker
        versions git info was not stored at all, so upgrading to a new
        CodeChecker results the storage of git blame info even for files that
        are already stored. For this reason we can't avoid an update on File
        and FileContent tables, but we can avoid double reading of blame info
        json files.
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
                compressed_content = zlib.compress(
                    source_file_content, zlib.Z_BEST_COMPRESSION)

                if session.bind.dialect.name == 'postgresql':
                    insert_stmt = sqlalchemy.dialects.postgresql \
                        .insert(FileContent).values(
                            content_hash=content_hash,
                            content=compressed_content,
                            blame_info=None).on_conflict_do_nothing(
                                index_elements=['content_hash'])

                    session.execute(insert_stmt)
                else:
                    fc = FileContent(content_hash, compressed_content, None)
                    session.add(fc)

                session.commit()
            except sqlalchemy.exc.IntegrityError:
                # Other transaction moght have added the same content in
                # the meantime.
                session.rollback()

    def __store_checker_identifiers(self, checkers: Set[Tuple[str, str]]):
        """
        Stores the identifiers "(analyzer, checker_name)" in the database into
        a look-up table where each unique checker is given a unique numeric
        identifier.

        Due to the use of an M-to-N connection table
        (see `AnalysisInfoChecker`) one side of the joins must have their IDs
        eagerly populated, otherwise the Python bindings will fail.
        However, eager population will result in exceptions that a flush was
        created before the transaction was complete.

        Moreover, this is performed separately from the storing of the details
        of a run to reduce contention if two parallel stores, especially across
        server instances (in a distributed/load-balanced environment) want to
        store the same identifier(s).
        """
        max_tries, tries, wait_time = 3, 0, timedelta(seconds=30)
        # The "fake" checker is a temporary row that is needed intermittently
        # during report storage because there might be reports that point to
        # checkers which are not found in a preemptively parsed
        # 'metadata.json', or, in the worst case, there might simply not be
        # a 'metadata.json' at all in the to-be-stored structure.
        all_checkers = {FakeChecker, UnknownChecker} | checkers
        while tries < max_tries:
            tries += 1
            try:
                LOG.debug("[%s] Begin attempt %d...", self._name, tries)
                with DBSession(self.__product.session_factory) as session:
                    known_checkers = {(r.analyzer_name, r.checker_name)
                                      for r in session
                                      .query(Checker.analyzer_name,
                                             Checker.checker_name)
                                      .all()}
                    for analyzer, checker in \
                            sorted(all_checkers - known_checkers):
                        s = self.__package_context.checker_labels \
                            .severity(checker)
                        s = ttypes.Severity._NAMES_TO_VALUES[s]
                        session.add(Checker(analyzer, checker, s))
                        LOG.debug("Acquiring ID for checker '%s/%s' "
                                  "for the first time.", analyzer, checker)

                    session.commit()
                    return
            except (sqlalchemy.exc.OperationalError,
                    sqlalchemy.exc.ProgrammingError,
                    sqlalchemy.exc.IntegrityError) as ex:
                LOG.error("Storing checkers of run '%s' failed: %s.\n"
                          "Waiting %d before trying again...",
                          self._name, ex, wait_time)
                time.sleep(wait_time.total_seconds())
                wait_time *= 2
            except Exception as ex:
                LOG.error("Failed to store checkers due to some other error: "
                          "%s", ex)
                import traceback
                traceback.print_exc()
                raise

        raise ConnectionRefusedError("Storing the names of the checkers in "
                                     "the run failed due to excessive "
                                     "contention!")

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
                    if self._version == '6.9.0':
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

                    # Obtain the ID eagerly to be able to use the M-to-N table.
                    session.add(analysis_info)
                    session.flush()
                    session.refresh(analysis_info, ["id"])

                    for analyzer in mip.analyzers:
                        q = session \
                            .query(Checker) \
                            .filter(Checker.analyzer_name == analyzer)
                        db_checkers = {r.checker_name: r for r in q.all()}

                        connection_rows = [AnalysisInfoChecker(
                            analysis_info, db_checkers[chk], is_enabled)
                            for chk, is_enabled
                            in mip.checkers.get(analyzer, {}).items()]
                        for r in connection_rows:
                            session.add(r)

                run_history.analysis_info.append(analysis_info)
                self.__analysis_info[src_dir_path] = analysis_info

    def __add_or_update_run(
        self,
        session: DBSession,
        run_history_time: datetime
    ) -> Tuple[int, bool]:
        """
        Store run related data to the database.
        By default updates the results if name already exists.
        Using the force flag removes existing analysis results for a run.
        """
        LOG.debug("Adding run '%s'...", self._name)

        run = session.query(Run) \
            .filter(Run.name == self._name) \
            .one_or_none()

        update_run = True
        if run and self._force:
            # Clean already collected results.
            if not run.can_delete:
                # Deletion is already in progress.
                msg = f"Can't delete {run.id}"
                LOG.debug(msg)
                raise EnvironmentError(msg)

            LOG.info('Removing previous analysis results...')
            session.delete(run)
            # Not flushing after delete leads to a constraint violation
            # error later, when adding run entity with the same name as
            # the old one.
            session.flush()

            checker_run = Run(self._name, self._version)
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
            checker_run = Run(self._name, self._version)
            session.add(checker_run)
            session.flush()
            run_id = checker_run.id
            update_run = False

        # Add run to the history.
        LOG.debug("Adding run history.")

        if self._tag is not None:
            run_history = session.query(RunHistory) \
                .filter(RunHistory.run_id == run_id,
                        RunHistory.version_tag == self._tag) \
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
            run_id, self._tag, self._user_name, run_history_time,
            cc_version, self._description)

        session.add(run_history)
        session.flush()

        LOG.debug("Adding run done.")

        self.__store_analysis_statistics(session, run_history.id)
        self.__store_analysis_info(session, run_history)

        session.flush()
        LOG.debug("Storing analysis statistics done.")

        return run_id, update_run

    def __get_checker(self,
                      session: DBSession,
                      analyzer_name: str,
                      checker_name: str) -> Optional[Checker]:
        try:
            return self.__checker_row_cache[(analyzer_name, checker_name)]
        except KeyError:
            maybe_orm: Optional[Checker] = session.query(Checker) \
                .filter(sqlalchemy.and_(
                    Checker.analyzer_name == analyzer_name,
                    Checker.checker_name == checker_name)) \
                .one_or_none()
            if maybe_orm:
                self.__checker_row_cache[(analyzer_name, checker_name)] = \
                    cast(Checker, maybe_orm)
            return maybe_orm

    def __checker_for_report(self,
                             session: DBSession,
                             report: Report) -> Optional[Checker]:
        analyzer_name, checker_name = checker_name_for_report(report)
        return self.__get_checker(session, analyzer_name, checker_name)

    def __add_report(
        self,
        session: DBSession,
        run_id: int,
        report: Report,
        report_path_hash: str,
        file_path_to_id: Dict[str, int],
        review_status: SourceReviewStatus,
        detection_status: str,
        detection_time: datetime,
        run_history_time: datetime,
        analysis_info: Optional[AnalysisInfo],
        fixed_at: Optional[datetime] = None
    ) -> int:
        """ Add report to the database. """
        checker = self.__checker_for_report(session, report)
        if not checker:
            # It would be too easy to create a 'Checker' instance with the
            # observed data right here, but __add_report() is called in
            # the context of the *BIG* TRANSACTION which has all the
            # reports of the entire store pending. Losing all that
            # information on a potential UNIQUE CONSTRAINT violation due
            # to multiple concurrent massStoreRun()s trying to store the
            # same checker ID which was never seen in a 'metadata.json' is
            # not worth it.
            checker = self.__get_checker(session,
                                         FakeChecker[0], FakeChecker[1])
            if not checker:
                LOG.fatal("Psuedo-checker '%s/%s' has no "
                          "identity in the database, even though "
                          "__store_checker_identifiers() should have "
                          "always preemptively created it!",
                          FakeChecker[0], FakeChecker[1])
                raise KeyError(FakeChecker[1])

        db_report = DBReport(
            file_path_to_id[report.file.path], run_id, report.report_hash,
            checker, report.line, report.column,
            len(report.bug_path_events), report.message, detection_status,
            review_status.status, review_status.author,
            review_status.message, run_history_time,
            review_status.in_source, detection_time, fixed_at)
        if analysis_info:
            db_report.analysis_info.append(analysis_info)

        session.add(db_report)
        self.__added_reports.append((db_report, report))
        if db_report.checker.checker_name == FakeChecker[1]:
            self.__reports_with_fake_checkers[report_path_hash] = \
                (report, db_report)

        return db_report.id

    def __get_faked_checkers(self) \
            -> Set[Tuple[str, str]]:
        """
        Extracts the "real" checker identifiers from the
        __reports_with_fake_checkers that might contain some yet not fully
        handled reports by __add_report(). This function does NOT touch the
        database!
        """
        return set(checker_name_for_report(report)
                   for report, _
                   in self.__reports_with_fake_checkers.values())

    def __load_report_ids_for_reports_with_fake_checkers(self, session):
        """
        Transforms the __reports_with_fake_checkers data structure by loading
        the report.id column in place for the DBReport ORM objects to allow
        __realise_fake_checkers() to execute appropriately.

        This must only be run **once** between the __add_report() sequence and
        the __realise_fake_checkers() operation. The reports **MUST** have
        been committed prior.
        """
        for rph, (report, db_report) in \
                self.__reports_with_fake_checkers.items():
            # Only load the "id" field from the database, not the entire row.
            session.refresh(db_report, ["id"])
            self.__reports_with_fake_checkers[rph] = (report, db_report.id)

    def __realise_fake_checkers(self, session):
        """
        __add_report() might leave some reports that have checker names in
        their data that were not found in the usually full checker list
        available in the 'metadata.json'. This usually happens if the report
        directory that is being stored is not from an 'analyze' or 'check'
        invocation (that would create an appropriate 'metadata.json') but from
        other tools (e.g., report-converter, or Cppcheck's native PLISTs).

        This function assumes that for each report in the
        __reports_with_fake_checkers, their actual checkers' IDs are now added
        added to the database (which was not the case when __add_report() ran),
        so all it does is upgrade the 'checker_id' FOREIGN KEY field to point
        at the real checker.
        """
        grouped_by_checker: Dict[Tuple[str, str], List[int]] = \
            defaultdict(list)
        for _, (report, db_id) in \
                self.__reports_with_fake_checkers.items():
            checker: Tuple[str, str] = checker_name_for_report(report)
            grouped_by_checker[checker].append(cast(int, db_id))

        for chk, report_ids in grouped_by_checker.items():
            analyzer_name, checker_name = chk
            chk_obj = cast(Checker, self.__get_checker(session,
                                                       analyzer_name,
                                                       checker_name))
            session.query(DBReport) \
                .filter(DBReport.id.in_(report_ids)) \
                .update({"checker_id": chk_obj.id},
                        synchronize_session=False)

    def __add_report_context(self, session, file_path_to_id):
        for db_report, report in self.__added_reports:
            LOG.debug("Storing bug path positions.")
            for i, p in enumerate(report.bug_path_positions):
                session.add(BugReportPoint(
                    p.range.start_line, p.range.start_col,
                    p.range.end_line, p.range.end_col,
                    i, file_path_to_id[p.file.path], db_report.id))

            LOG.debug("Storing bug path events.")
            for i, event in enumerate(report.bug_path_events):
                session.add(BugPathEvent(
                    event.range.start_line, event.range.start_col,
                    event.range.end_line, event.range.end_col,
                    i, event.message, file_path_to_id[event.file.path],
                    db_report.id))

            LOG.debug("Storing notes.")
            for note in report.notes:
                data_type = report_extended_data_type_str(
                    ttypes.ExtendedReportDataType.NOTE)

                session.add(ExtendedReportData(
                    note.range.start_line, note.range.start_col,
                    note.range.end_line, note.range.end_col,
                    note.message, file_path_to_id[note.file.path],
                    db_report.id, data_type))

            LOG.debug("Storing macro expansions.")
            for macro in report.macro_expansions:
                data_type = report_extended_data_type_str(
                    ttypes.ExtendedReportDataType.MACRO)

                session.add(ExtendedReportData(
                    macro.range.start_line, macro.range.start_col,
                    macro.range.end_line, macro.range.end_col,
                    macro.message, file_path_to_id[macro.file.path],
                    db_report.id, data_type))

            if report.annotations:
                self.__validate_and_add_report_annotations(
                    session, db_report.id, report.annotations)

        session.flush()

    def __process_report_file(
        self,
        report_file_path: str,
        session: DBSession,
        run_id: int,
        file_path_to_id: Dict[str, int],
        run_history_time: datetime,
        skip_handler: skiplist_handler.SkipListHandler,
        review_status_handler: ReviewStatusHandler,
        hash_map_reports: Dict[str, List[Any]]
    ) -> bool:
        """
        Process and save reports from the given report file to the database.
        """
        reports = report_file.get_reports(report_file_path)

        if not reports:
            return True

        def get_missing_file_ids(report: Report) -> List[str]:
            """ Returns file paths which database file id is missing. """
            missing_ids_for_files = []
            for file_path in report.trimmed_files:
                file_id = file_path_to_id.get(file_path, -1)
                if file_id == -1:
                    missing_ids_for_files.append(file_path)

            return missing_ids_for_files

        root_dir_path = os.path.dirname(report_file_path)
        mip = self.__mips[root_dir_path]
        analysis_info = self.__analysis_info.get(root_dir_path)

        for report in reports:
            self.__report_count += 1
            report.trim_path_prefixes(self._trim_path_prefixes)

            missing_ids_for_files = get_missing_file_ids(report)
            if missing_ids_for_files:
                LOG.warning("Failed to get database id for file path '%s'! "
                            "Skip adding report: %s:%d:%d [%s]",
                            ' '.join(missing_ids_for_files), report.file.path,
                            report.line, report.column, report.checker_name)
                continue

            self.__all_report_checkers.add(report.checker_name)

            if skip_handler.should_skip(report.file.original_path):
                continue

            report_path_hash = get_report_path_hash(report)
            if report_path_hash in self.__already_added_report_hashes:
                LOG.debug('Not storing report. Already added: %s', report)
                continue

            LOG.debug("Storing report to the database...")

            detection_status = 'new'
            detected_at = run_history_time

            old_report = None
            if report.report_hash in hash_map_reports:
                old_report = hash_map_reports[report.report_hash][0]
                old_status = old_report.detection_status
                detection_status = 'reopened' \
                    if old_status == 'resolved' else 'unresolved'
                detected_at = old_report.detected_at

            report.analyzer_name = mip.checker_to_analyzer.get(
                report.checker_name, report.analyzer_name)

            review_status = SourceReviewStatus()

            try:
                review_status = review_status_handler.get_review_status(report)
            except ValueError as err:
                self.__wrong_src_code_comments.append(str(err))

            review_status.author = self._user_name
            review_status.date = run_history_time

            # False positive and intentional reports are considered as closed
            # reports which is indicated with non-null "fixed_at" date.
            fixed_at = None
            if review_status.status in ['false_positive', 'intentional']:
                # Keep in mind that now this is not handling review status
                # rules, only review status source code comments
                if old_report and old_report.review_status in \
                        ['false_positive', 'intentional']:
                    fixed_at = old_report.fixed_at
                else:
                    fixed_at = run_history_time

            self.__check_report_count()
            self.__add_report(session, run_id, report, report_path_hash,
                              file_path_to_id, review_status, detection_status,
                              detected_at, run_history_time, analysis_info,
                              fixed_at)

            self.__new_report_hashes[report.report_hash] = \
                review_status.status
            self.__already_added_report_hashes.add(report_path_hash)

            LOG.debug("Storing report done. "
                      "path_hash=%s, bug_id/report_hash=%s, source_file=%s",
                      report_path_hash, report.report_hash, report_file_path)

        return True

    def __validate_and_add_report_annotations(
        self,
        session: DBSession,
        report_id: int,
        report_annotation: Dict
    ):
        """
        This function checks the format of the annotations. For example a
        "timestamp" annotation must be in datetime format. If the format
        doesn't match then an exception is thrown. In case of proper format the
        annotation is added to the database.
        """
        for key, value in report_annotation.items():
            try:
                # String conversion is for normalizing the format. For example,
                # "2000-01-01T10:20" timestamp will be stored as
                # "2000-01-01 10:20".
                value = str(report_annotation_types[key]["func"](value))
                session.add(ReportAnnotations(report_id, key, value))
            except KeyError:
                # pylint: disable=raise-missing-from
                raise RequestFailed(
                    ErrorCode.REPORT_FORMAT,
                    f"'{key}' is not an allowed report annotation.",
                    report_annotation_types.keys())
            except ValueError:
                # pylint: disable=raise-missing-from
                raise RequestFailed(
                    ErrorCode.REPORT_FORMAT,
                    f"'{value}' has wrong format. '{key}' annotations must be "
                    f"'{report_annotation_types[key]['display']}'.")

    def __get_report_limit_for_product(self):
        with DBSession(self.__config_database) as session:
            product = session.query(Product).get(self.__product.id)
            if product.report_limit:
                self.__report_limit = product.report_limit

    def __check_report_count(self):
        """
        This method comparest the already added report count to the report
        limit, Raises exception if the number of reports is more than the
        that is configured for the product.
        """
        if len(self.__added_reports) >= self.__report_limit:
            LOG.error("The number of reports in the given report folder is " +
                      "larger than the allowed." +
                      f"The limit: {self.__report_limit}!")
            raise OverflowError(
                "**Report Limit Exceeded** " +
                "This report folder cannot be stored because the number of " +
                "reports in the result folder is too high. Usually noisy " +
                "checkers, generating a lot of reports are not useful and " +
                "it is better to disable them. Run `CodeChecker parse " +
                "<report_folder>` to gain a better understanding on report " +
                "counts. Disable checkers that have generated an excessive " +
                "number of reports and then rerun the analysis to be able " +
                "to store the results on the server. " +
                f"Limit: {self.__report_limit}")

    def __store_reports(
        self,
        session: DBSession,
        report_dir: Path,
        source_root: Path,
        run_id: int,
        file_path_to_id: Dict[str, int],
        run_history_time: datetime
    ):
        """ Parse up and store the plist report files. """

        def get_skip_handler(
            report_dir: Path
        ) -> skiplist_handler.SkipListHandler:
            """ Get a skip list handler based on the given report directory."""
            skip_file_path = report_dir / "skip_file"
            if not skip_file_path.exists():
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
        self.__new_report_hashes = {}
        self.__all_report_checkers = set()

        all_reports = session.query(DBReport) \
            .filter(DBReport.run_id == run_id) \
            .all()

        report_to_report_id = defaultdict(list)
        for db_report in all_reports:
            report_to_report_id[db_report.bug_id].append(db_report)

        enabled_checkers: Set[str] = set()
        disabled_checkers: Set[str] = set()

        # Processing analyzer result files.
        processed_result_file_count = 0

        for root_dir_path, _, report_file_paths in os.walk(report_dir):
            LOG.debug("Get reports from '%s' directory", root_dir_path)

            skip_handler = get_skip_handler(Path(root_dir_path))
            review_status_handler = ReviewStatusHandler(str(source_root))

            review_status_cfg = \
                os.path.join(root_dir_path, 'review_status.yaml')
            if os.path.isfile(review_status_cfg):
                review_status_handler.set_review_status_config(
                    review_status_cfg)

            mip = self.__mips[root_dir_path]
            enabled_checkers.update(mip.enabled_checkers)
            disabled_checkers.update(mip.disabled_checkers)

            for f in report_file_paths:
                if not report_file.is_supported(f):
                    continue

                LOG.debug("Parsing input file '%s'", f)

                report_file_path = os.path.join(root_dir_path, f)
                self.__process_report_file(
                    report_file_path, session, run_id,
                    file_path_to_id, run_history_time,
                    skip_handler, review_status_handler, report_to_report_id)
                processed_result_file_count += 1

        session.flush()

        self.__add_report_context(session, file_path_to_id)
        # Get all relevant review_statuses for the newly stored reports
        # CHHECK: Call self.getReviewStatusRules instead of the below query
        # but before first check the performance
        reports_to_rs_rules = session.query(ReviewStatusRule, DBReport) \
            .join(DBReport, DBReport.bug_id == ReviewStatusRule.bug_hash) \
            .filter(sqlalchemy.and_(
                DBReport.run_id == run_id,
                DBReport.review_status_is_in_source.is_(False)))

        # Set the newly stored reports
        for review_status, db_report in reports_to_rs_rules:
            if db_report.bug_id not in self.__new_report_hashes:
                continue
            old_report = None
            if db_report.bug_id in report_to_report_id:
                old_report = report_to_report_id[db_report.bug_id][0]
            fixed_at = None
            if review_status.status in ['false_positive', 'intentional']:
                # Keep in mind that now this is not handling review status
                # rules, only review status source code comments
                if old_report and old_report.review_status in \
                        ['false_positive', 'intentional']:
                    fixed_at = old_report.fixed_at
                else:
                    fixed_at = run_history_time

            db_report.review_status = review_status.status
            db_report.review_statuses_author = review_status.author
            db_report.review_status_message = review_status.message
            db_report.review_statuses_date = review_status.date
            db_report.fixed_at = fixed_at
            db_report.review_status_is_in_source = False

        session.flush()

        LOG.info("[%s] Processed %d analyzer result file(s).", self._name,
                 processed_result_file_count)

        # If a checker was found in a plist file it can not be disabled so we
        # will add this to the enabled checkers list and remove this checker
        # from the disabled checkers list.
        # Also if multiple report directories are stored and a checker was
        # enabled in one report directory but it was disabled in another
        # directory we will mark this checker as enabled.
        enabled_checkers |= self.__all_report_checkers
        disabled_checkers -= self.__all_report_checkers

        reports_to_delete = set()
        for bug_hash, reports in report_to_report_id.items():
            if bug_hash in self.__new_report_hashes:
                reports_to_delete.update([x.id for x in reports])
            else:
                for report in reports:
                    checker_name: str = report.checker.checker_name
                    if checker_name in disabled_checkers:
                        report.detection_status = 'off'
                    elif checker_is_unavailable(checker_name,
                                                enabled_checkers):
                        report.detection_status = 'unavailable'
                    else:
                        report.detection_status = 'resolved'

                    if report.fixed_at is None:
                        report.fixed_at = run_history_time

        if reports_to_delete:
            from .report_server import remove_reports
            remove_reports(session, reports_to_delete)

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

    def store(self,
              original_zip_size: int,
              time_spent_on_task_preparation: float):
        """Store run results to the server."""
        start_time = time.time()

        try:
            LOG.debug("Using unzipped folder '%s'", self._zip_dir)

            source_root = self._zip_dir / "root"
            blame_root = self._zip_dir / "blame"
            report_dir = self._zip_dir / "reports"
            filename_to_hash = load_json(
                self._zip_dir / "content_hashes.json", {})

            # Store information that is "global" on the product database level.
            with StepLog(self._name, "Store source files"):
                LOG.info("[%s] Storing %d source file(s).", self._name,
                         len(filename_to_hash.keys()))
                file_path_to_id = self.__store_source_files(
                    source_root, filename_to_hash)
                self.__add_blame_info(blame_root, filename_to_hash)

            run_history_time = datetime.now()

            with StepLog(self._name, "Parse 'metadata.json's"):
                for root_dir_path, _, _ in os.walk(report_dir):
                    metadata_file_path = os.path.join(
                        root_dir_path, 'metadata.json')

                    self.__mips[root_dir_path] = \
                        MetadataInfoParser(metadata_file_path)

            with StepLog(self._name,
                         "Store look-up ID for checkers in 'metadata.json'"):
                checkers_in_metadata = {
                    (analyzer, checker)
                    for metadata in self.__mips.values()
                    for analyzer in metadata.analyzers
                    for checker
                    in metadata.checkers.get(analyzer, {}).keys()}
                self.__store_checker_identifiers(checkers_in_metadata)

            try:
                # This session's transaction buffer stores the actual run data
                # into the database.
                with DBSession(self.__product.session_factory) as session, \
                        RunLock(session, self._name):
                    run_id, update_run = self.__add_or_update_run(
                        session, run_history_time)

                    with StepLog(self._name, "Store 'reports'"):
                        self.__store_reports(
                            session, report_dir, source_root, run_id,
                            file_path_to_id, run_history_time)

                    session.commit()
                    self.__load_report_ids_for_reports_with_fake_checkers(
                        session)

                if self.__reports_with_fake_checkers:
                    with StepLog(
                            self._name,
                            "Get look-up IDs for checkers not present in "
                            "'metadata.json'"):
                        additional_checkers = self.__get_faked_checkers()
                        # __store_checker_identifiers() has its own
                        # TRANSACTION!
                        self.__store_checker_identifiers(
                            additional_checkers)

                with DBSession(self.__product.session_factory) as session, \
                        RunLock(session, self._name):
                    # The data of the run has been successfully committed
                    # into the database. Deal with post-processing issues
                    # that could only be done after-the-fact.
                    if self.__reports_with_fake_checkers:
                        with StepLog(self._name,
                                     "Fix-up report-to-checker associations"):
                            self.__realise_fake_checkers(session)

                    self.finish_checker_run(session, run_id)
                    session.commit()

                end_time = time.time()

                # If the current store() updated an existing run, do not
                # increment the number of runs saved for the product.
                self.__product.set_cached_run_data(
                    self.__config_db,
                    number_of_runs_change=(0 if update_run else 1),
                    last_store_date=run_history_time)

                run_time: float = (end_time - start_time) + \
                    time_spent_on_task_preparation
                zip_size_kib: float = original_zip_size / 1024

                LOG.info("'%s' stored results (decompressed size: %.2f KiB) "
                         "to run '%s' (ID: %d%s) in %.2f seconds.",
                         self._user_name, zip_size_kib, self._name, run_id,
                         f", under tag '{self._tag}'" if self._tag else "",
                         run_time)

                iso_start_time = datetime.fromtimestamp(start_time) \
                    .isoformat()

                log_msg = f"{iso_start_time}, " \
                          f"{round(run_time, 2)}s, " \
                          f'"{self.__product.name}", ' \
                          f'"{self._name}", ' \
                          f"{round(zip_size_kib)}KiB, " \
                          f"{self.__report_count}, " \
                          f"{run_id}"

                STORE_TIME_LOG.info(log_msg)
            except (sqlalchemy.exc.OperationalError,
                    sqlalchemy.exc.ProgrammingError) as ex:
                LOG.error("Database error! Storing reports to the "
                          "database failed: %s", ex)
                raise
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
            with DBSession(self.__product.session_factory) as session:
                RunLock(session, self._name).drop_run_lock_from_db()

            if self.__wrong_src_code_comments:
                wrong_files_as_table = twodim.to_str(
                    "table",
                    ["File", "Line", "Checker name"],
                    [wrong_comment.split('|', 3)
                     for wrong_comment in self.__wrong_src_code_comments])

                raise ValueError("One or more source files contained invalid "
                                 "source code comments! "
                                 "Failed to set review statuses.\n\n"
                                 f"{wrong_files_as_table}")
