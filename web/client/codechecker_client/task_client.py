# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Implementation for the ``CodeChecker cmd serverside-tasks`` subcommand.
"""
from argparse import Namespace
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import time
from typing import Callable, Dict, List, Optional, Tuple, cast

from codechecker_api_shared.ttypes import Ternary
from codechecker_api.ProductManagement_v6.ttypes import Product
from codechecker_api.codeCheckerServersideTasks_v6.ttypes import \
    AdministratorTaskInfo, TaskFilter, TaskInfo, TaskStatus

from codechecker_common import logger
from codechecker_common.util import clamp
from codechecker_report_converter import twodim

from .client import setup_product_client, setup_task_client
from .helpers.product import ThriftProductHelper
from .helpers.tasks import ThriftServersideTaskHelper
from .product import split_server_url


# Needs to be set in the handler functions.
LOG: Optional[logger.logging.Logger] = None


def init_logger(level, stream=None, logger_name="system"):
    logger.setup_logger(level, stream)

    global LOG
    LOG = logger.get_logger(logger_name)


class TaskTimeoutError(Exception):
    """Indicates that `await_task_termination` timed out."""

    def __init__(self, token: str, task_status: int, delta: timedelta):
        super().__init__(f"Task '{token}' is still "
                         f"'{TaskStatus._VALUES_TO_NAMES[task_status]}', "
                         f"but did not have any progress for '{delta}' "
                         f"({delta.total_seconds()} seconds)!")


def await_task_termination(
    log: logger.logging.Logger,
    token: str,
    probe_delta_min: timedelta = timedelta(seconds=5),
    probe_delta_max: timedelta = timedelta(minutes=2),
    timeout_from_last_task_progress: Optional[timedelta] = timedelta(hours=1),
    max_consecutive_request_failures: Optional[int] = 10,
    task_api_client: Optional[ThriftServersideTaskHelper] = None,
    server_address: Optional[Tuple[str, str, str]] = None,
) -> str:
    """
    Blocks the execution of the current process until the task specified by
    `token` terminates.
    When terminated, returns the task's `TaskStatus` as a string.

    `await_task_termination` sleeps the current process (as with
    `time.sleep`), and periodically wakes up, with a distance of wake-ups
    calculated between `probe_delta_min` and `probe_delta_max`, to check the
    status of the task by downloading ``getTaskInfo()`` result from the
    server.

    The server to use is specified by either providing a valid
    `task_api_client`, at which point the connection of the existing client
    will be reused; or by providing a
    ``(protocol: str, host: str, port: int)`` tuple under `server_address`,
    which will cause `await_task_termination` to set the Task API client up
    internally.

    This call blocks the caller stack frame indefinitely, unless
    `timeout_from_last_task_progress` is specified.
    If so, the function will unblock by raising `TaskTimeoutError` if the
    specified time has elapsed since the queried task last exhibited forward
    progress.
    Forward progress is calculated from the task's ``startedAt`` timestamp,
    the ``completedAt`` timestamp, or the ``lastHeartbeat``, whichever is
    later in time.
    For tasks that had not started executing yet (their ``startedAt`` is
    `None`), this timeout does not apply.

    This function is resillient against network problems and request failures
    through the connection to the server, if
    `max_consecutive_request_failures` is specified.
    If so, it will wait the given number of Thrift client failures before
    giving up.
    """
    if not task_api_client and not server_address:
        raise ValueError("Specify 'task_api_client' or 'server_address' "
                         "to point the function at a server to probe!")
    if not task_api_client and server_address:
        protocol, host, port = server_address
        task_api_client = setup_task_client(protocol, host, port)
    if not task_api_client:
        raise ConnectionError("Failed to set up Task API client!")

    probe_distance: timedelta = deepcopy(probe_delta_min)
    request_failures: int = 0
    last_forward_progress_by_task: Optional[datetime] = None
    task_status: int = TaskStatus.ALLOCATED

    def _query_task_status():
        while True:
            nonlocal request_failures
            try:
                ti = task_api_client.getTaskInfo(token)
                request_failures = 0
                break
            except SystemExit:
                # getTaskInfo() is decorated by @thrift_client_call, which
                # raises SystemExit by calling sys.exit() internally, if
                # something fails.
                request_failures += 1
                if max_consecutive_request_failures and request_failures > \
                        max_consecutive_request_failures:
                    raise
                log.info("Retrying task status query [%d / %d retries] ...",
                         request_failures, max_consecutive_request_failures)

        last_forward_progress_by_task: Optional[datetime] = None
        epoch_to_consider: int = 0
        if ti.completedAtEpoch:
            epoch_to_consider = ti.completedAtEpoch
        elif ti.lastHeartbeatEpoch:
            epoch_to_consider = ti.lastHeartbeatEpoch
        elif ti.startedAtEpoch:
            epoch_to_consider = ti.startedAtEpoch
        if epoch_to_consider:
            last_forward_progress_by_task = cast(
                datetime, _utc_epoch_to_datetime(epoch_to_consider))

        task_status = cast(int, ti.status)

        return last_forward_progress_by_task, task_status

    while True:
        task_forward_progressed_at, task_status = _query_task_status()
        if task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED,
                           TaskStatus.CANCELLED, TaskStatus.DROPPED]:
            break

        if task_forward_progressed_at:
            time_since_last_progress = datetime.now(timezone.utc) \
                - task_forward_progressed_at
            if timeout_from_last_task_progress and \
                    time_since_last_progress >= \
                    timeout_from_last_task_progress:
                log.error("'%s' timeout elapsed since task last progressed "
                          "at '%s', considering "
                          "hung/locked out/lost/failed...",
                          timeout_from_last_task_progress,
                          task_forward_progressed_at)
                raise TaskTimeoutError(token, task_status,
                                       time_since_last_progress)

            if last_forward_progress_by_task:
                # Tune the next probe's wait period in a fashion similar to
                # TCP's low-level AIMD (addition increment,
                # multiplicative decrement) algorithm.
                time_between_last_two_progresses = \
                    last_forward_progress_by_task - task_forward_progressed_at
                if not time_between_last_two_progresses:
                    # No progress since the last probe, increase the timeout
                    # until the next probe, and hope that some progress will
                    # have been made by that time.
                    probe_distance += timedelta(seconds=1)
                elif time_between_last_two_progresses <= 2 * probe_distance:
                    # time_between_last_two_progresses is always at least
                    # probe_distance, because it is the distance between two
                    # queried and observed forward progress measurements.
                    # However, if they are "close enough" to each other, it
                    # means that the server is progressing well with the task
                    # and it is likely that the task might be finished "soon".
                    #
                    # In this case, it is beneficial to INCREASE the probing
                    # frequency, in order not to make the user wait "too much"
                    # before observing a "likely" soon available success.
                    probe_distance /= 2
                else:
                    # If the progresses detected from the server are
                    # "far apart", it can indicate that the server is busy
                    # with processing the task.
                    #
                    # In this case, DECREASING the frequency if beneficial,
                    # because it is "likely" that a final result will not
                    # arrive soon, and keeping the current frequency would
                    # just keep "flooding" the server with queries that do
                    # not return a meaningfully different result.
                    probe_distance += timedelta(seconds=1)
            else:
                # If the forward progress has not been observed yet at all,
                # increase the timeout until the next probe, and hope that
                # some progress will have been made by that time.
                probe_distance += timedelta(seconds=1)

            # At any rate, always keep the probe_distance between the
            # requested limits.
            probe_distance = \
                clamp(probe_delta_min, probe_distance, probe_delta_max)

            last_forward_progress_by_task = task_forward_progressed_at

        log.debug("Waiting %f seconds (%s) before querying the server...",
                  probe_distance.total_seconds(), probe_distance)
        time.sleep(probe_distance.total_seconds())

    return TaskStatus._VALUES_TO_NAMES[task_status]


def _datetime_to_utc_epoch(d: Optional[datetime]) -> Optional[int]:
    return int(d.replace(tzinfo=timezone.utc).timestamp()) if d else None


def _utc_epoch_to_datetime(s: Optional[int]) -> Optional[datetime]:
    return datetime.fromtimestamp(s, timezone.utc) if s else None


def _datetime_to_str(d: Optional[datetime]) -> Optional[str]:
    return d.strftime("%Y-%m-%d %H:%M:%S") if d else None


def _build_filter(args: Namespace,
                  product_id_to_endpoint: Dict[int, str],
                  get_product_api: Callable[[], ThriftProductHelper]) \
        -> Optional[TaskFilter]:
    """Build a `TaskFilter` from the command-line `args`."""
    filter_: Optional[TaskFilter] = None

    def get_filter() -> TaskFilter:
        nonlocal filter_
        if not filter_:
            filter_ = TaskFilter()
        return filter_

    if args.machine_id:
        get_filter().machineIDs = args.machine_id
    if args.type:
        get_filter().kinds = args.type
    if args.status:
        get_filter().statuses = [TaskStatus._NAMES_TO_VALUES[s.upper()]
                                 for s in args.status]
    if args.username:
        get_filter().usernames = args.username
    elif args.no_username:
        get_filter().filterForNoUsername = True
    if args.product:
        # Users specify products via ENDPOINTs for U.X. friendliness, but the
        # API works with product IDs.
        def _get_product_id_or_log(endpoint: str) -> Optional[int]:
            try:
                products: List[Product] = cast(
                    List[Product],
                    get_product_api().getProducts(endpoint, None))
                # Endpoints substring-match.
                product = next(p for p in products if p.endpoint == endpoint)
                p_id = cast(int, product.id)
                product_id_to_endpoint[p_id] = endpoint
                return p_id
            except StopIteration:
                LOG.warning("No product with endpoint '%s', omitting it from "
                            "the query.",
                            endpoint)
                return None

        get_filter().productIDs = list(filter(lambda i: i is not None,
                                              map(_get_product_id_or_log,
                                                  args.product)))
    elif args.no_product:
        get_filter().filterForNoProductID = True
    if args.enqueued_before:
        get_filter().enqueuedBeforeEpoch = _datetime_to_utc_epoch(
            args.enqueued_before)
    if args.enqueued_after:
        get_filter().enqueuedAfterEpoch = _datetime_to_utc_epoch(
            args.enqueued_after)
    if args.started_before:
        get_filter().startedBeforeEpoch = _datetime_to_utc_epoch(
            args.started_before)
    if args.started_after:
        get_filter().startedAfterEpoch = _datetime_to_utc_epoch(
            args.started_after)
    if args.finished_before:
        get_filter().completedBeforeEpoch = _datetime_to_utc_epoch(
            args.finished_before)
    if args.finished_after:
        get_filter().completedAfterEpoch = _datetime_to_utc_epoch(
            args.finished_after)
    if args.last_seen_before:
        get_filter().heartbeatBeforeEpoch = _datetime_to_utc_epoch(
            args.started_before)
    if args.last_seen_after:
        get_filter().heartbeatAfterEpoch = _datetime_to_utc_epoch(
            args.started_after)
    if args.only_cancelled:
        get_filter().cancelFlag = Ternary._NAMES_TO_VALUES["ON"]
    elif args.no_cancelled:
        get_filter().cancelFlag = Ternary._NAMES_TO_VALUES["OFF"]
    if args.only_consumed:
        get_filter().consumedFlag = Ternary._NAMES_TO_VALUES["ON"]
    elif args.no_consumed:
        get_filter().consumedFlag = Ternary._NAMES_TO_VALUES["OFF"]

    return filter_


def _unapi_info(ti: TaskInfo) -> dict:
    """
    Converts a `TaskInfo` API structure into a flat Pythonic `dict` of
    non-API types.
    """
    return {**{k: v
               for k, v in ti.__dict__.items()
               if k != "status" and not k.endswith("Epoch")},
            **{k.replace("Epoch", "", 1):
               _datetime_to_str(_utc_epoch_to_datetime(v))
               for k, v in ti.__dict__.items()
               if k.endswith("Epoch")},
            **{"status": TaskStatus._VALUES_TO_NAMES[cast(int, ti.status)]},
            }


def _unapi_admin_info(ati: AdministratorTaskInfo) -> dict:
    """
    Converts a `AdministratorTaskInfo` API structure into a flat Pythonic
    `dict` of non-API types.
    """
    return {**{k: v
               for k, v in ati.__dict__.items()
               if k != "normalInfo"},
            **_unapi_info(cast(TaskInfo, ati.normalInfo)),
            }


def _transform_product_ids_to_endpoints(
    task_infos: List[dict],
    product_id_to_endpoint: Dict[int, str],
    get_product_api: Callable[[], ThriftProductHelper]
):
    """Replace ``task_infos[N]["productId"]`` with
    ``task_infos[N]["productEndpoint"]`` for all elements.
    """
    for ti in task_infos:
        try:
            ti["productEndpoint"] = \
                product_id_to_endpoint[ti["productId"]] \
                if ti["productId"] != 0 else None
        except KeyError:
            # Take the slow path, and get the ID->Endpoint map from the server.
            product_id_to_endpoint = {
                product.id: product.endpoint
                for product
                in get_product_api().getProducts(None, None)}
        del ti["productId"]


def handle_tasks(args: Namespace) -> int:
    """Main method for the ``CodeChecker cmd serverside-tasks`` subcommand."""
    # If the given output format is not `table`, redirect the logger's output
    # to standard error.
    init_logger(args.verbose if "verbose" in args else None,
                "stderr" if "output_format" in args
                and args.output_format != "table"
                else None)

    rc: int = 0
    protocol, host, port = split_server_url(args.server_url)
    api = setup_task_client(protocol, host, port)

    if "TEST_WORKSPACE" in os.environ and "dummy_task_args" in args:
        timeout, should_fail = \
            int(args.dummy_task_args[0]), \
            args.dummy_task_args[1].lower() in ["y", "yes", "true", "1", "on"]

        dummy_task_token = api.createDummyTask(timeout, should_fail)
        LOG.info("Dummy task created with token '%s'.", dummy_task_token)
        if not args.token:
            args.token = [dummy_task_token]
        else:
            args.token.append(dummy_task_token)

    # Lazily initialise a Product manager API client as well, it can be needed
    # if products are being put into a request filter, or product-specific
    # tasks appear on the output.
    product_api: Optional[ThriftProductHelper] = None
    product_id_to_endpoint: Dict[int, str] = {}

    def get_product_api() -> ThriftProductHelper:
        nonlocal product_api
        if not product_api:
            product_api = setup_product_client(protocol, host, port)
        return product_api

    tokens_of_tasks: List[str] = []
    task_filter = _build_filter(args,
                                product_id_to_endpoint,
                                get_product_api)
    if task_filter:
        # If the "filtering" API must be used, the args.token list should also
        # be part of the filter.
        task_filter.tokens = args.token

        admin_task_infos: List[AdministratorTaskInfo] = \
            api.getTasks(task_filter)

        # Save the tokens of matched tasks for later, in case we have to do
        # some further processing.
        if args.cancel_task or args.wait_and_block:
            tokens_of_tasks = [cast(str, ti.normalInfo.token)
                               for ti in admin_task_infos]

        task_info_for_print = list(map(_unapi_admin_info,
                                       admin_task_infos))
        _transform_product_ids_to_endpoints(task_info_for_print,
                                            product_id_to_endpoint,
                                            get_product_api)

        if args.output_format == "json":
            print(json.dumps(task_info_for_print))
        else:
            if args.output_format == "plaintext":
                # For the listing of the tasks, the "table" format is more
                # appropriate, so we intelligently switch over to that.
                args.output_format = "table"

            headers = ["Token", "Machine", "Type", "Summary", "Status",
                       "Product", "User", "Enqueued", "Started", "Last seen",
                       "Completed", "Cancelled?"]
            rows = []
            for ti in task_info_for_print:
                rows.append((ti["token"],
                             ti["machineId"],
                             ti["taskKind"],
                             ti["summary"],
                             ti["status"],
                             ti["productEndpoint"] or "",
                             ti["actorUsername"] or "",
                             ti["enqueuedAt"] or "",
                             ti["startedAt"] or "",
                             ti["lastHeartbeat"] or "",
                             ti["completedAt"] or "",
                             "Yes" if ti["cancelFlagSet"] else "",
                             ))
            print(twodim.to_str(args.output_format, headers, rows))
    else:
        # If the filtering API was not used, we need to query the tasks
        # directly, based on their token.
        if not args.token:
            LOG.error("ERROR! To use 'CodeChecker cmd serverside-tasks', "
                      "a '--token' list or some other filter criteria "
                      "**MUST** be specified!")
            sys.exit(2)  # Simulate argparse error code.

        # Otherwise, query the tasks, and print their info.
        task_infos: List[TaskInfo] = [api.getTaskInfo(token)
                                      for token in args.token]
        if not task_infos:
            LOG.error("No tasks retrieved for the specified tokens!")
            return 1

        if args.wait_and_block or args.cancel_task:
            # If we need to do something with the tasks later, save the tokens.
            tokens_of_tasks = args.token

        task_info_for_print = list(map(_unapi_info, task_infos))
        _transform_product_ids_to_endpoints(task_info_for_print,
                                            product_id_to_endpoint,
                                            get_product_api)

        if len(task_infos) == 1:
            # If there was exactly one task in the query, the return code
            # of the program should be based on the status of the task.
            ti = task_info_for_print[0]
            if ti["status"] == "COMPLETED":
                rc = 0
            elif ti["status"] == "FAILED":
                rc = 4
            elif ti["status"] in ["ALLOCATED", "ENQUEUED", "RUNNING"]:
                rc = 8
            elif ti["status"] in ["CANCELLED", "DROPPED"]:
                rc = 16
            else:
                raise ValueError(f"Unknown task status '{ti['status']}'!")

        if args.output_format == "json":
            print(json.dumps(task_info_for_print))
        else:
            if len(task_infos) > 1 or args.output_format != "plaintext":
                if args.output_format == "plaintext":
                    # For the listing of the tasks, if there are multiple, the
                    # "table" format is more appropriate, so we intelligently
                    # switch over to that.
                    args.output_format = "table"

                headers = ["Token", "Type", "Summary", "Status", "Product",
                           "User", "Enqueued", "Started", "Last seen",
                           "Completed", "Cancelled by administrators?"]
                rows = []
                for ti in task_info_for_print:
                    rows.append((ti["token"],
                                 ti["taskKind"],
                                 ti["summary"],
                                 ti["status"],
                                 ti["productEndpoint"] or "",
                                 ti["actorUsername"] or "",
                                 ti["enqueuedAt"] or "",
                                 ti["startedAt"] or "",
                                 ti["lastHeartbeat"] or "",
                                 ti["completedAt"] or "",
                                 "Yes" if ti["cancelFlagSet"] else "",
                                 ))

                print(twodim.to_str(args.output_format, headers, rows))
            else:
                # Otherwise, for exactly ONE task, in "plaintext" mode, print
                # the details for humans to read.
                ti = task_info_for_print[0]
                product_line = \
                    f"    - Product:      {ti['productEndpoint']}\n" \
                    if ti["productEndpoint"] else ""
                user_line = f"    - User:         {ti['actorUsername']}\n" \
                    if ti["actorUsername"] else ""
                cancel_line = "    - Cancelled by administrators!\n" \
                    if ti["cancelFlagSet"] else ""
                print(f"Task '{ti['token']}':\n"
                      f"    - Type:         {ti['taskKind']}\n"
                      f"    - Summary:      {ti['summary']}\n"
                      f"    - Status:       {ti['status']}\n"
                      f"{product_line}"
                      f"{user_line}"
                      f"    - Enqueued at:  {ti['enqueuedAt'] or ''}\n"
                      f"    - Started at:   {ti['startedAt'] or ''}\n"
                      f"    - Last seen:    {ti['lastHeartbeat'] or ''}\n"
                      f"    - Completed at: {ti['completedAt'] or ''}\n"
                      f"{cancel_line}"
                      )
                if ti["comments"]:
                    print(f"Comments on task '{ti['token']}':\n")
                    for line in ti["comments"].split("\n"):
                        if not line or line == "----------":
                            # Empty or separator lines.
                            print(line)
                        elif " at " in line and line.endswith(":"):
                            # Lines with the "header" for who made the comment
                            # and when.
                            print(line)
                        else:
                            print(f"> {line}")

    if args.cancel_task:
        for token in tokens_of_tasks:
            this_call_cancelled = api.cancelTask(token)
            if this_call_cancelled:
                LOG.info("Submitted cancellation request for task '%s'.",
                         token)
            else:
                LOG.debug("Task '%s' had already been cancelled.", token)

    if args.wait_and_block:
        rc = 0
        for token in tokens_of_tasks:
            LOG.info("Awaiting the completion of task '%s' ...", token)
            status: str = await_task_termination(
                cast(logger.logging.Logger, LOG),
                token,
                task_api_client=api)
            if status != "COMPLETED":
                if args.cancel_task:
                    # If '--kill' was specified, keep the return code 0
                    # if the task was successfully cancelled as well.
                    if status != "CANCELLED":
                        LOG.error("Task '%s' error status: %s!",
                                  token, status)
                        rc = 1
                    else:
                        LOG.info("Task '%s' terminated in status:  %s.",
                                 token, status)
                else:
                    LOG.error("Task '%s' error status: %s!", token, status)
                    rc = 1
            else:
                LOG.info("Task '%s' terminated in status: %s.", token, status)

    return rc
