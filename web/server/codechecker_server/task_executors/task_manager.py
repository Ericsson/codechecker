# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Contains status management and query methods to handle bookkeeping for
dispatched background tasks.
"""
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Callable, Optional

import sqlalchemy

from codechecker_common.compatibility.multiprocessing import Pipe, Queue, Value
from codechecker_common.logger import get_logger, signal_log
from codechecker_common.util import generate_random_token

from ..database.config_db_model import BackgroundTask as DBTask, Product
from ..database.database import DBSession

MAX_TOKEN_RANDOM_RETRIES = 10
CHARS_INVALID_IN_PATH = re.compile(r"[\'\"<>:\\/\|\*\?\. ]")

LOG = get_logger("server")


class ExecutorInProgressShutdownError(Exception):
    """
    Exception raised to indicate that the background executors are under
    shutdown.
    """
    def __init__(self):
        super().__init__("Task executor is shutting down!")


class TaskManager:
    """
    Handles the creation of "Task" status objects in the database and pushing
    in-memory `AbstractTask` subclass instances to a `Queue`.

    This class is instantiatied for EVERY WORKER separately, and is not a
    shared resource!
    """

    def __init__(self,
                 q: Queue,
                 task_pipes,
                 config_db_session_factory,
                 server_environment,
                 executor_kill_flag: Value,
                 machine_id: str,
                 temp_dir: Optional[Path] = None):
        self._queue = q
        self._database_factory = config_db_session_factory
        self._server_environment = server_environment
        self._is_shutting_down = executor_kill_flag
        self._machine_id = machine_id
        self._temp_dir_root = (temp_dir or Path(tempfile.gettempdir())) \
            / "codechecker_tasks" \
            / CHARS_INVALID_IN_PATH.sub('_', machine_id)
        self.__task_pipes = task_pipes

        os.makedirs(self._temp_dir_root, exist_ok=True)

    @property
    def configuration_database_session_factory(self):
        """
        Returns a `sqlalchemy.orm.sessionmaker` instance for the server
        configuration database.
        """
        return self._database_factory

    @property
    def environment(self):
        """Returns the ``check_env`` injected into the task manager."""
        return self._server_environment

    @property
    def machine_id(self) -> str:
        """Returns the ``machine_id`` the instance was constructed with."""
        return self._machine_id

    def allocate_task_record(self, kind: str, summary: str,
                             user_name: Optional[str],
                             product: Optional[Product] = None) -> str:
        """
        Creates the token and the status record for a new task with the given
        initial metadata.

        Returns the token of the task, which is a unique identifier of the
        allocated record.
        """
        try_count: int = 0
        while True:
            with DBSession(self._database_factory) as session:
                try:
                    token = generate_random_token(DBTask._token_length)

                    task = DBTask(token, kind, summary, self.machine_id,
                                  user_name, product)
                    session.add(task)
                    session.commit()

                    return token
                except sqlalchemy.exc.IntegrityError as ie:
                    # The only failure that can happen is the PRIMARY KEY's
                    # UNIQUE violation, which means we hit jackpot by
                    # generating an already used token!
                    try_count += 1

                    if try_count >= MAX_TOKEN_RANDOM_RETRIES:
                        raise KeyError(
                            "Failed to generate a unique ID for task "
                            f"{kind} ({summary}) after "
                            f"{MAX_TOKEN_RANDOM_RETRIES} retries!") from ie

    def create_task_data(self, token: str) -> Path:
        """
        Creates a temporary directory which is **NOT** cleaned up
        automatically by the current context, and which is suitable for
        putting arbitrary files underneath to communicate large inputs
        (that should not be put in the `Queue`) to the `execute` method of
        an `AbstractTask`.

        The larger business logic of the Server implementation may still clean
        up the temporary directories, e.g., if the pending tasks are being
        dropped during a shutdown, making retention of this "temporary data"
        useless.
        See `destroy_temporary_data`.
        """
        task_temp_dir = tempfile.mkdtemp(prefix=f"{token}-",
                                         dir=self._temp_dir_root)
        return Path(task_temp_dir)

    def destroy_all_temporary_data(self):
        """
        Removes the contents of task-temporary directories under the
        `TaskManager`'s initial `temp_dir` and current "machine ID".
        """
        try:
            shutil.rmtree(self._temp_dir_root)
        except Exception as ex:
            LOG.warning("Failed to remove background tasks' data_dirs at "
                        "'%s':\n%s", self._temp_dir_root, str(ex))

    def drop_all_incomplete_tasks(self, action: str) -> int:
        """
        Sets all tasks in the database that were associated with the given
        `machine_id` to ``"dropped"`` status, indicating that the status was
        changed during the `action`.

        Returns the number of `DBTask`s actually changed.
        """
        count: int = 0
        with DBSession(self._database_factory) as session:
            for task in session.query(DBTask) \
                    .filter(DBTask.machine_id == self.machine_id,
                            DBTask.status.in_(["allocated",
                                               "enqueued",
                                               "running"])) \
                    .all():
                count += 1
                task.add_comment(f"DROPPED!\n{action}", "SYSTEM")
                task.set_abandoned(force_dropped_status=True)

            session.commit()
        return count

    def get_task_record(self, token: str) -> DBTask:
        """
        Retrieves the `DBTask` for the task identified by `task_obj`.

        This class should not be mutated, only the fields queried.
        """
        with DBSession(self._database_factory) as session:
            db_task: Optional[DBTask] = session.get(DBTask, token)
            if not db_task:
                raise KeyError(f"No task record for token '{token}' "
                               "in the database")
            session.expunge(db_task)
            return db_task

    def _get_task_record(self, task_obj: "AbstractTask") -> DBTask:
        """
        Retrieves the `DBTask` for the task identified by `task_obj`.

        This class should not be mutated, only the fields queried.
        """
        return self.get_task_record(task_obj.token)

    def _mutate_task_record(self, task_obj: "AbstractTask",
                            mutator: Callable[[DBTask], None]):
        """
        Executes the given `mutator` function for the `DBTask` record
        corresponding to the `task_obj` description available in memory.
        """
        with DBSession(self._database_factory) as session:
            db_task: Optional[DBTask] = session.get(DBTask, task_obj.token)
            if not db_task:
                raise KeyError(f"No task record for token '{task_obj.token}' "
                               "in the database")

            try:
                mutator(db_task)
            except Exception:
                session.rollback()

                import traceback
                traceback.print_exc()
                raise

            session.commit()

    def push_task(self, task_obj: "AbstractTask"):
        """Enqueues the given `task_obj` onto the `Queue`."""
        if self.is_shutting_down:
            raise ExecutorInProgressShutdownError()

        # Note, that the API handler process calling push_task() might be
        # killed before writing to the queue, so an actually enqueued task
        # (according to the DB) might never be consumed by a background
        # process.
        # As we have to COMMIT the status change before the actual processing
        # in order to show the time stamp to the user(s), there is no better
        # way to make this more atomic.
        try:
            self._mutate_task_record(task_obj, lambda dbt: dbt.set_enqueued())
            self.__task_pipes[task_obj.token] = Pipe(duplex=False)
            self._queue.put(task_obj)
        except SystemExit as sex:
            try:
                signal_log(LOG, "WARNING", f"Process #{os.getpid()}: "
                           "push_task() killed via SystemExit during "
                           f"enqueue of task '{task_obj.token}'!")

                def _log_and_abandon(db_task: DBTask):
                    db_task.add_comment(
                        "SHUTDOWN!\nEnqueueing process terminated during the "
                        "ongoing enqueue! The task will never be executed!",
                        "SYSTEM[TaskManager::push_task()]")
                    db_task.set_abandoned(force_dropped_status=True)

                self._mutate_task_record(task_obj, _log_and_abandon)
                self._send_done_message(task_obj.token)
            finally:
                raise sex

    def get_task_receiver_pipe(self, task_token: str):
        """
        Returns the pipe to the task receiver process.
        """
        return self.__task_pipes[task_token][0]

    def _send_done_message(self, task_token: str):
        """
        Sends a message to the task receiver process to indicate that the task
        has been completed.
        """
        self.__task_pipes[task_token][1].send(None)
        del self.__task_pipes[task_token]

    @property
    def is_shutting_down(self) -> bool:
        """
        Returns whether the shutdown flag for the executor associated with the
        `TaskManager` had been set.
        """
        return self._is_shutting_down.value

    def should_cancel(self, task_obj: "AbstractTask") -> bool:
        """
        Returns whether the task identified by `task_obj` should be
        co-operatively cancelled.
        """
        db_task = self._get_task_record(task_obj)
        return self.is_shutting_down or \
            (db_task.status in ["enqueued", "running"]
             and db_task.cancel_flag)

    def add_comment(self, task_obj: "AbstractTask", comment: str,
                    actor: Optional[str] = None):
        """
        Adds `comment` in the name of `actor` to the task record corresponding
        to `task_obj`.
        """
        self._mutate_task_record(task_obj,
                                 lambda dbt: dbt.add_comment(comment, actor))

    def heartbeat(self, task_obj: "AbstractTask"):
        """
        Triggers ``heartbeat()`` timestamp update in the database for
        `task_obj`.
        """
        self._mutate_task_record(task_obj, lambda dbt: dbt.heartbeat())
