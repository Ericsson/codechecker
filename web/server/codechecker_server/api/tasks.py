
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handle Thrift requests for background task management.
"""
import datetime
import os
import time
from typing import Dict, List, Optional

from sqlalchemy.sql.expression import and_, or_

from codechecker_api_shared.ttypes import RequestFailed, ErrorCode, Ternary
from codechecker_api.codeCheckerServersideTasks_v6.ttypes import \
    AdministratorTaskInfo, TaskFilter, TaskInfo, TaskStatus

from codechecker_common.logger import get_logger

from codechecker_server.profiler import timeit

from ..database.config_db_model import BackgroundTask as DBTask, Product
from ..database.database import DBSession, conv
from ..task_executors.abstract_task import AbstractTask, TaskCancelHonoured
from ..task_executors.task_manager import TaskManager
from .. import permissions
from .common import exc_to_thrift_reqfail

LOG = get_logger("server")


class TestingDummyTask(AbstractTask):
    """Implementation of task object created by ``createDummyTask()``."""
    def __init__(self, token: str, timeout: int, should_fail: bool):
        super().__init__(token, None)
        self.timeout = timeout
        self.should_fail = should_fail

    def _implementation(self, tm: TaskManager) -> None:
        counter: int = 0
        while counter < self.timeout:
            tm.heartbeat(self)

            counter += 1
            LOG.debug("Dummy task ticking... [%d / %d]",
                      counter, self.timeout)

            if tm.should_cancel(self):
                LOG.info("Dummy task '%s' was %s at tick [%d / %d]!",
                         self.token,
                         "KILLED BY SHUTDOWN" if tm.is_shutting_down
                         else "CANCELLED BY ADMIN",
                         counter,
                         self.timeout)
                raise TaskCancelHonoured(self)

            time.sleep(1)

        if self.should_fail:
            raise ValueError("Task self-failure as per the user's request.")


def _db_timestamp_to_posix_epoch(d: Optional[datetime.datetime]) \
        -> Optional[int]:
    return int(d.replace(tzinfo=datetime.timezone.utc).timestamp()) if d \
        else None


def _posix_epoch_to_db_timestamp(s: Optional[int]) \
        -> Optional[datetime.datetime]:
    return datetime.datetime.fromtimestamp(s, datetime.timezone.utc) if s \
        else None


def _make_task_info(t: DBTask) -> TaskInfo:
    """Format API `TaskInfo` from `DBTask`."""
    return TaskInfo(
        token=t.token,
        taskKind=t.kind,
        status=TaskStatus._NAMES_TO_VALUES[t.status.upper()],
        productId=t.product_id or 0,
        actorUsername=t.username,
        summary=t.summary,
        comments=t.comments,
        enqueuedAtEpoch=_db_timestamp_to_posix_epoch(t.enqueued_at),
        startedAtEpoch=_db_timestamp_to_posix_epoch(t.started_at),
        completedAtEpoch=_db_timestamp_to_posix_epoch(t.finished_at),
        lastHeartbeatEpoch=_db_timestamp_to_posix_epoch(
            t.last_seen_at),
        cancelFlagSet=t.cancel_flag,
    )


def _make_admin_task_info(t: DBTask) -> AdministratorTaskInfo:
    """Format API `AdministratorTaskInfo` from `DBTask`."""
    return AdministratorTaskInfo(
        normalInfo=_make_task_info(t),
        machineId=t.machine_id,
        statusConsumed=t.consumed,
    )


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
class ThriftTaskHandler:
    """
    Manages Thrift requests concerning the user-facing Background Tasks API.
    """

    def __init__(self,
                 configuration_database_sessionmaker,
                 task_manager: TaskManager,
                 auth_session):
        self._config_db = configuration_database_sessionmaker
        self._task_manager = task_manager
        self._auth_session = auth_session

    def _get_username(self) -> Optional[str]:
        """
        Returns the actually logged in user name.
        """
        return self._auth_session.user if self._auth_session else None

    @exc_to_thrift_reqfail
    @timeit
    def getTaskInfo(self, token: str) -> TaskInfo:
        """
        Returns the `TaskInfo` for the task identified by `token`.
        """
        with DBSession(self._config_db) as session:
            db_task: Optional[DBTask] = session.query(DBTask).get(token)
            if not db_task:
                raise RequestFailed(ErrorCode.GENERAL,
                                    f"Task '{token}' does not exist!")

            has_right_to_query_status: bool = False
            should_set_consumed_flag: bool = False

            if db_task.username == self._get_username():
                has_right_to_query_status = True
                should_set_consumed_flag = db_task.is_in_terminated_state
            elif db_task.product_id is not None:
                associated_product: Optional[Product] = \
                    session.query(Product).get(db_task.product_id)
                if not associated_product:
                    LOG.error("No product with ID '%d', but a task is "
                              "associated with it.",
                              db_task.product_id)
                else:
                    has_right_to_query_status = \
                        permissions.require_permission(
                            permissions.PRODUCT_ADMIN,
                            {"config_db_session": session,
                             "productID": associated_product.id},
                            self._auth_session)

            if not has_right_to_query_status:
                has_right_to_query_status = permissions.require_permission(
                    permissions.SUPERUSER,
                    {"config_db_session": session},
                    self._auth_session)

            if not has_right_to_query_status:
                raise RequestFailed(
                    ErrorCode.UNAUTHORIZED,
                    "Only the task's submitter, a PRODUCT_ADMIN (of the "
                    "product the task is associated with), or a SUPERUSER "
                    "can getTaskInfo()!")

            info = _make_task_info(db_task)

            if should_set_consumed_flag:
                db_task.consumed = True
                session.commit()

            return info

    @exc_to_thrift_reqfail
    @timeit
    def getTasks(self, filters: TaskFilter) -> List[AdministratorTaskInfo]:
        """Obtain tasks matching the `filters` for administrators."""
        with DBSession(self._config_db) as session:
            if filters.productIDs is not None and not filters.productIDs:
                if not permissions.require_permission(
                        permissions.SUPERUSER,
                        {"config_db_session": session},
                        self._auth_session):
                    raise RequestFailed(
                        ErrorCode.UNAUTHORIZED,
                        "Querying service tasks (not associated with a "
                        "product) requires SUPERUSER privileges!")
            if filters.productIDs:
                no_admin_products = [
                    prod_id for prod_id in filters.productIDs
                    if not permissions.require_permission(
                        permissions.PRODUCT_ADMIN,
                        {"config_db_session": session, "productID": prod_id},
                        self._auth_session)]
                if no_admin_products:
                    no_admin_products = [session.query(Product)
                                         .get(product_id).endpoint
                                         for product_id in no_admin_products]
                    # pylint: disable=consider-using-f-string
                    raise RequestFailed(ErrorCode.UNAUTHORIZED,
                                        "Querying product tasks requires "
                                        "PRODUCT_ADMIN rights, but it is "
                                        "missing from product(s): '%s'!"
                                        % ("', '".join(no_admin_products)))

            AND = []
            if filters.tokens:
                AND.append(or_(*(DBTask.token.ilike(conv(token))
                                 for token in filters.tokens)))

            if filters.machineIDs:
                AND.append(or_(*(DBTask.machine_id.ilike(conv(machine_id))
                                 for machine_id in filters.machineIDs)))

            if filters.kinds:
                AND.append(or_(*(DBTask.kind.ilike(conv(kind))
                                 for kind in filters.kinds)))

            if filters.statuses:
                AND.append(or_(DBTask.status.in_([
                    TaskStatus._VALUES_TO_NAMES[status].lower()
                    for status in filters.statuses])))

            if filters.usernames is not None:
                if filters.usernames:
                    AND.append(or_(*(DBTask.username.ilike(conv(username))
                                     for username in filters.usernames)))
                else:
                    AND.append(DBTask.username.is_(None))

            if filters.productIDs is not None:
                if filters.productIDs:
                    AND.append(or_(DBTask.product_id.in_(filters.productIDs)))
                else:
                    AND.append(DBTask.product_id.is_(None))

            if filters.enqueuedBeforeEpoch:
                AND.append(DBTask.enqueued_at <= _posix_epoch_to_db_timestamp(
                    filters.enqueuedBeforeEpoch))

            if filters.enqueuedAfterEpoch:
                AND.append(DBTask.enqueued_at >= _posix_epoch_to_db_timestamp(
                    filters.enqueuedAfterEpoch))

            if filters.startedBeforeEpoch:
                AND.append(DBTask.started_at <= _posix_epoch_to_db_timestamp(
                    filters.startedBeforeEpoch))

            if filters.startedAfterEpoch:
                AND.append(DBTask.started_at >= _posix_epoch_to_db_timestamp(
                    filters.startedAfterEpoch))

            if filters.completedBeforeEpoch:
                AND.append(DBTask.finished_at <= _posix_epoch_to_db_timestamp(
                    filters.completedBeforeEpoch))

            if filters.completedAfterEpoch:
                AND.append(DBTask.finished_at >= _posix_epoch_to_db_timestamp(
                    filters.completedAfterEpoch))

            if filters.heartbeatBeforeEpoch:
                AND.append(DBTask.last_seen_at <=
                           _posix_epoch_to_db_timestamp(
                               filters.heartbeatBeforeEpoch))

            if filters.heartbeatAfterEpoch:
                AND.append(DBTask.last_seen_at >=
                           _posix_epoch_to_db_timestamp(
                               filters.heartbeatAfterEpoch))

            if filters.cancelFlag:
                if filters.cancelFlag == Ternary._NAMES_TO_VALUES["OFF"]:
                    AND.append(DBTask.cancel_flag.is_(False))
                elif filters.cancelFlag == Ternary._NAMES_TO_VALUES["ON"]:
                    AND.append(DBTask.cancel_flag.is_(True))

            if filters.consumedFlag:
                if filters.consumedFlag == Ternary._NAMES_TO_VALUES["OFF"]:
                    AND.append(DBTask.consumed.is_(False))
                elif filters.consumedFlag == Ternary._NAMES_TO_VALUES["ON"]:
                    AND.append(DBTask.consumed.is_(True))

            ret: List[AdministratorTaskInfo] = []
            has_superuser: Optional[bool] = None
            product_admin_rights: Dict[int, bool] = {}
            for db_task in session.query(DBTask).filter(and_(*AND)).all():
                if not db_task.product_id:
                    # Tasks associated with the server, and not a specific
                    # product, should only be visible to SUPERUSERs.
                    if has_superuser is None:
                        has_superuser = permissions.require_permission(
                            permissions.SUPERUSER,
                            {"config_db_session": session},
                            self._auth_session)
                    if not has_superuser:
                        continue
                else:
                    # Tasks associated with a product should only be visible
                    # to PRODUCT_ADMINs of that product.
                    try:
                        if not product_admin_rights[db_task.product_id]:
                            continue
                    except KeyError:
                        product_admin_rights[db_task.product_id] = \
                            permissions.require_permission(
                                permissions.PRODUCT_ADMIN,
                                {"config_db_session": session,
                                 "productID": db_task.product_id},
                                self._auth_session)
                        if not product_admin_rights[db_task.product_id]:
                            continue

                ret.append(_make_admin_task_info(db_task))

            return ret

    @exc_to_thrift_reqfail
    @timeit
    def cancelTask(self, token: str) -> bool:
        """
        Sets the ``cancel_flag`` of the task specified by `token` to `True`
        in the database, **REQUESTING** that the task gracefully terminate
        itself.

        There are no guarantees that tasks will respect this!
        """
        with DBSession(self._config_db) as session:
            if not permissions.require_permission(
                    permissions.SUPERUSER,
                    {"config_db_session": session},
                    self._auth_session):
                raise RequestFailed(
                    ErrorCode.UNAUTHORIZED,
                    "cancelTask() requires server-level SUPERUSER rights.")

            db_task: Optional[DBTask] = session.query(DBTask).get(token)
            if not db_task:
                raise RequestFailed(ErrorCode.GENERAL,
                                    f"Task '{token}' does not exist!")

            if not db_task.can_be_cancelled:
                return False

            db_task.add_comment("SUPERUSER requested cancellation.",
                                self._get_username())
            db_task.cancel_flag = True
            session.commit()

            return True

    @exc_to_thrift_reqfail
    @timeit
    def createDummyTask(self, timeout: int, should_fail: bool) -> str:
        """
        Used for testing purposes only.

        This function will **ALWAYS** throw an exception when ran outside of a
        testing environment.
        """
        if "TEST_WORKSPACE" not in os.environ:
            raise RequestFailed(ErrorCode.GENERAL,
                                "createDummyTask() is only available in "
                                "testing environments!")

        token = self._task_manager.allocate_task_record(
            "TaskService::DummyTask",
            "Dummy task for testing purposes",
            self._get_username(),
            None)

        t = TestingDummyTask(token, timeout, should_fail)
        self._task_manager.push_task(t)

        return token
