# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Implements a dedicated subprocess that deals with running `AbstractTask`
subclasses in the background.
"""
from datetime import timedelta
import os
from queue import Empty
import signal

from sqlalchemy.orm import sessionmaker

from codechecker_common.compatibility.multiprocessing import Queue, Value
from codechecker_common.logger import get_logger, signal_log

from ..database.config_db_model import BackgroundTask as DBTask
from .abstract_task import AbstractTask
from .task_manager import TaskManager


WAIT_TIME_FOR_TASK_QUEUE_CLEARING_AT_SERVER_SHUTDOWN = timedelta(seconds=5)

LOG = get_logger("server")


def executor(queue: Queue,
             config_db_sql_server,
             server_shutdown_flag: "Value",
             machine_id: str):
    """
    The "main()" function implementation for a background task executor
    process.

    This process sets up the state of the local process, and then deals with
    popping jobs from the queue and executing them in the local context.
    """
    # First things first, a background worker process should NOT respect the
    # termination signals received from the parent process, because it has to
    # run its own cleanup logic before shutting down.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    kill_flag = Value('B', False)

    def executor_hangup_handler(signum: int, _frame):
        """
        Handle SIGHUP (1) to do a graceful shutdown of the background worker.
        """
        if signum not in [signal.SIGHUP]:
            signal_log(LOG, "ERROR", "Signal "
                       f"<{signal.Signals(signum).name} ({signum})> "
                       "handling attempted by 'executor_hangup_handler'!")
            return

        signal_log(LOG, "DEBUG", f"{os.getpid()}: Received "
                   f"{signal.Signals(signum).name} ({signum}), preparing for "
                   "shutdown ...")
        kill_flag.value = True

    signal.signal(signal.SIGHUP, executor_hangup_handler)

    config_db_engine = config_db_sql_server.create_engine()
    tm = TaskManager(queue, sessionmaker(bind=config_db_engine), kill_flag,
                     machine_id)

    while not kill_flag.value:
        try:
            # Do not block indefinitely when waiting for a job, to allow
            # checking whether the kill flags were set.
            t: AbstractTask = queue.get(block=True, timeout=1)
        except Empty:
            continue

        import pprint
        LOG.info("Executor #%d received task object:\n\n%s:\n%s\n\n",
                 os.getpid(), t, pprint.pformat(t.__dict__))

        t.execute(tm)

    # Once the main loop of task execution process has finished, there might
    # still be tasks left in the queue.
    # If the server is shutting down (this is distinguished from the local kill
    # flag, because a 'SIGHUP' might arrive from any source, not just a valid
    # graceful shutdown!), then these jobs would be lost if the process just
    # exited, with no information reported to the database.
    # We need set these tasks to dropped as much as possible.
    def _log_shutdown_and_abandon(db_task: DBTask):
        db_task.add_comment("SHUTDOWN!\nTask never started due to the "
                            "server shutdown!", "SYSTEM")
        db_task.set_abandoned(force_dropped_status=True)

    def _drop_task_at_shutdown(t: AbstractTask):
        try:
            LOG.debug("Dropping task '%s' due to server shutdown...", t.token)
            tm._mutate_task_record(t, _log_shutdown_and_abandon)
        except Exception:
            pass
        finally:
            t.destroy_data()

    if server_shutdown_flag.value:
        # Unfortunately, it is not guaranteed which process will wake up first
        # when popping objects from the queue.
        # Blocking indefinitely would not be a solution here, because all
        # producers (API threads) had likely already exited at this point.
        # However, simply observing no elements for a short period of time is
        # also not enough, as at the very last moments of a server's lifetime,
        # one process might observe the queue to be empty, simply because
        # another process stole the object that was put into it.
        #
        # To be on the safe side of things, we require to observe the queue to
        # be *constantly* empty over a longer period of repetitive sampling.
        empty_sample_count: int = 0
        while empty_sample_count < int(
                WAIT_TIME_FOR_TASK_QUEUE_CLEARING_AT_SERVER_SHUTDOWN
                .total_seconds()):
            try:
                t: AbstractTask = queue.get(block=True, timeout=1)
            except Empty:
                empty_sample_count += 1
                continue

            empty_sample_count = 0
            _drop_task_at_shutdown(t)

    queue.close()
    queue.join_thread()

    try:
        config_db_engine.dispose()
    except Exception as ex:
        LOG.error("Failed to shut down task executor!\n%s", str(ex))
        return

    LOG.debug("Task executor subprocess PID %d exited main loop.",
              os.getpid())
