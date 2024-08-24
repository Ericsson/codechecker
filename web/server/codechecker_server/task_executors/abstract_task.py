# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Contains the base class to be inherited and implemented by all background task
types.
"""
import logging
import os
import pathlib
import shutil
from typing import Optional

from codechecker_common.logger import get_logger

from ..database.config_db_model import BackgroundTask as DBTask


LOG = get_logger("server")


class TaskCancelHonoured(Exception):
    """
    Specialised tag exception raised by `AbstractTask` implementations in a
    checkpoint after having checked that their ``cancel_flag`` was set, in
    order to terminate task-specific execution and to register the
    cancellation's success by the `AbstractTask.execute` method.

    This exception should **NOT** be caught by user code.
    """

    def __init__(self, task_obj: "AbstractTask"):
        super().__init__(f"Task '{task_obj.token}' honoured CANCEL request.")
        self.task_obj = task_obj


class AbstractTask:
    """
    Base class implementing common execution and bookkeeping methods to
    facilitate the dispatch of tasks to background worker processes.

    Instances of this class **MUST** be marshallable by ``pickle``, as they
    are transported over an IPC `Queue`.
    It is important that instances do not grow too large, as the underlying
    OS-level primitives of a `Queue` can get full, which can result in a
    deadlock situation.

    The run-time contents of the instance should only contain the bare minimum
    metadata required for the implementation to execute in the background.

    Implementors of subclasses **MAY REASONABLY ASSUME** that an
    `AbstractTask` scheduled in the API handler process of a server will be
    actually executed by a background worker in the same process group, on the
    same machine instance.
    """

    def __init__(self, token: str, data_path: Optional[pathlib.Path]):
        self._token = token
        self._data_path = data_path

    @property
    def token(self) -> str:
        """Returns the task's identifying token, its primary ID."""
        return self._token

    @property
    def data_path(self) -> Optional[pathlib.Path]:
        """
        Returns the filesystem path where the task's input data is prepared.
        """
        return self._data_path

    def destroy_data(self):
        """
        Deletes the contents of `data_path`.
        """
        if not self._data_path:
            return

        try:
            shutil.rmtree(self._data_path)
            LOG.debug("Wiping temporary data of task '%s' at '%s' ...",
                      self._token, self._data_path)
        except Exception as ex:
            LOG.warning("Failed to remove background task's data_dir at "
                        "'%s':\n%s", self.data_path, str(ex))

    def _implementation(self, _task_manager: "TaskManager") -> None:
        """
        Implemented by subclasses to perform the logic specific to the task.

        Subclasses should use the `task_manager` object, injected from the
        context of the executed subprocess, to query and mutate service-level
        information about the current task.
        """
        raise NotImplementedError(f"No implementation for task class {self}!")

    def execute(self, task_manager: "TaskManager") -> None:
        """
        Executes the `_implementation` of the task, overridden by subclasses,
        to perform a task-specific business logic.

        This high-level wrapper deals with capturing `Exception`s, setting
        appropriate status information in the database (through the
        injected `task_manager`) and logging failures accordingly.
        """
        if task_manager.should_cancel(self):
            def _log_cancel_and_abandon(db_task: DBTask):
                db_task.add_comment("CANCEL!\nTask cancelled before "
                                    "execution began!",
                                    "SYSTEM[AbstractTask::execute()]")
                db_task.set_abandoned(force_dropped_status=False)

            task_manager._mutate_task_record(self, _log_cancel_and_abandon)
            return

        try:
            task_manager._mutate_task_record(
                self, lambda dbt: dbt.set_running())
        except KeyError:
            # KeyError is thrown if a task without a corresponding database
            # record is attempted to be executed.
            LOG.error("Failed to execute task '%s' due to database exception",
                      self.token)
        except Exception as ex:
            LOG.error("Failed to execute task '%s' due to database exception"
                      "\n%s",
                      self.token, str(ex))
            # For any other record, try to set the task abandoned due to an
            # exception.
            try:
                task_manager._mutate_task_record(
                    self, lambda dbt:
                    dbt.set_abandoned(force_dropped_status=True))
            except Exception:
                return

        LOG.debug("Task '%s' running on machine '%s' executor #%d",
                  self.token, task_manager.machine_id, os.getpid())

        try:
            self._implementation(task_manager)
            LOG.debug("Task '%s' finished on machine '%s' executor #%d",
                      self.token,
                      task_manager.machine_id,
                      os.getpid())

            try:
                task_manager._mutate_task_record(
                    self, lambda dbt: dbt.set_finished(successfully=True))
            except Exception as ex:
                LOG.error("Failed to set task '%s' finished due to "
                          "database exception:\n%s",
                          self.token, str(ex))
        except TaskCancelHonoured:
            def _log_cancel_and_abandon(db_task: DBTask):
                db_task.add_comment("CANCEL!\nCancel request of admin "
                                    "honoured by task.",
                                    "SYSTEM[AbstractTask::execute()]")
                db_task.set_abandoned(force_dropped_status=False)

            def _log_drop_and_abandon(db_task: DBTask):
                db_task.add_comment("SHUTDOWN!\nTask honoured graceful "
                                    "cancel signal generated by "
                                    "server shutdown.",
                                    "SYSTEM[AbstractTask::execute()]")
                db_task.set_abandoned(force_dropped_status=True)

            if not task_manager.is_shutting_down:
                task_manager._mutate_task_record(self, _log_cancel_and_abandon)
            else:
                task_manager._mutate_task_record(self, _log_drop_and_abandon)
        except Exception as ex:
            LOG.error("Failed to execute task '%s' on machine '%s' "
                      "executor #%d: %s",
                      self.token, task_manager.machine_id, os.getpid(),
                      str(ex))
            import traceback
            traceback.print_exc()

            def _log_exception_and_fail(db_task: DBTask):
                db_task.add_comment(
                    f"FAILED!\nException during execution:\n{str(ex)}",
                    "SYSTEM[AbstractTask::execute()]")
                if LOG.isEnabledFor(logging.DEBUG):
                    db_task.add_comment("Debug exception information:\n"
                                        f"{traceback.format_exc()}",
                                        "SYSTEM[AbstractTask::execute()]")
                db_task.set_finished(successfully=False)

            task_manager._mutate_task_record(self, _log_exception_and_fail)
        finally:
            self.destroy_data()
