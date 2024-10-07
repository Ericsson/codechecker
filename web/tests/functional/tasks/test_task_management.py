# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Contains tests of the ``"/Tasks"`` API endpoint to query, using the
``DummyTask``, normal task management related API functions.
"""
from copy import deepcopy
from datetime import datetime, timezone
import os
import pathlib
import shutil
import unittest
import time
from typing import List, Optional, cast

import multiprocess

from codechecker_api_shared.ttypes import RequestFailed, Ternary
from codechecker_api.codeCheckerServersideTasks_v6.ttypes import \
    AdministratorTaskInfo, TaskFilter, TaskInfo, TaskStatus

from libtest import codechecker, env


# Stop events for the CodeChecker servers.
STOP_SERVER = multiprocess.Event()
STOP_SERVER_AUTH = multiprocess.Event()
STOP_SERVER_NO_AUTH = multiprocess.Event()

TEST_WORKSPACE: Optional[str] = None


# Note: Test names in this file follow a strict ordinal convention, because
# the assertions are created with a specific execution history!

class TaskManagementAPITests(unittest.TestCase):
    def setup_class(self):
        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace("tasks")
        os.environ["TEST_WORKSPACE"] = TEST_WORKSPACE

        codechecker_cfg = {
            "check_env": env.test_env(TEST_WORKSPACE),
            "workspace": TEST_WORKSPACE,
            "checkers": [],
            "viewer_host": "localhost",
            "viewer_port": env.get_free_port(),
            "viewer_product": "tasks",
        }

        # Run a normal server that is only used to manage the
        # "test_package_product".
        codechecker.start_server(codechecker_cfg, STOP_SERVER,
                                 ["--machine-id", "workspace-manager"])

        codechecker_cfg_no_auth = deepcopy(codechecker_cfg)
        codechecker_cfg_no_auth.update({
            "viewer_port": env.get_free_port(),
        })

        # Run a normal server which does not require authentication.
        codechecker.start_server(codechecker_cfg_no_auth, STOP_SERVER_NO_AUTH,
                                 ["--machine-id", "unprivileged"])

        codechecker_cfg_auth = deepcopy(codechecker_cfg)
        codechecker_cfg_auth.update({
            "viewer_port": env.get_free_port(),
        })

        # Run a privileged server which does require authentication.
        (pathlib.Path(TEST_WORKSPACE) / "root.user").unlink()
        env.enable_auth(TEST_WORKSPACE)
        codechecker.start_server(codechecker_cfg_auth, STOP_SERVER_AUTH,
                                 ["--machine-id", "privileged"])

        env.export_test_cfg(TEST_WORKSPACE,
                            {"codechecker_cfg": codechecker_cfg,
                             "codechecker_cfg_no_auth":
                             codechecker_cfg_no_auth,
                             "codechecker_cfg_auth": codechecker_cfg_auth})

        codechecker.add_test_package_product(codechecker_cfg, TEST_WORKSPACE)

    def teardown_class(self):
        # TODO: If environment variable is set keep the workspace and print
        # out the path.
        global TEST_WORKSPACE

        STOP_SERVER_NO_AUTH.set()
        STOP_SERVER_NO_AUTH.clear()
        STOP_SERVER_AUTH.set()
        STOP_SERVER_AUTH.clear()

        codechecker.remove_test_package_product(TEST_WORKSPACE)
        STOP_SERVER.set()
        STOP_SERVER.clear()

        print(f"Removing: {TEST_WORKSPACE}")
        shutil.rmtree(cast(str, TEST_WORKSPACE), ignore_errors=True)

    def setup_method(self, _):
        test_workspace = os.environ["TEST_WORKSPACE"]
        self._test_env = env.import_test_cfg(test_workspace)

        print(f"Running {self.__class__.__name__} tests in {test_workspace}")

        auth_server = self._test_env["codechecker_cfg_auth"]
        no_auth_server = self._test_env["codechecker_cfg_no_auth"]

        self._auth_client = env.setup_auth_client(test_workspace,
                                                  auth_server["viewer_host"],
                                                  auth_server["viewer_port"])

        root_token = self._auth_client.performLogin("Username:Password",
                                                    "root:root")
        admin_token = self._auth_client.performLogin("Username:Password",
                                                     "admin:admin123")

        self._anonymous_task_client = env.setup_task_client(
            test_workspace,
            no_auth_server["viewer_host"], no_auth_server["viewer_port"])
        self._admin_task_client = env.setup_task_client(
            test_workspace,
            auth_server["viewer_host"], auth_server["viewer_port"],
            session_token=admin_token)
        self._privileged_task_client = env.setup_task_client(
            test_workspace,
            auth_server["viewer_host"], auth_server["viewer_port"],
            session_token=root_token)

    def test_task_1_query_status(self):
        task_token = self._anonymous_task_client.createDummyTask(10, False)

        time.sleep(5)
        task_info: TaskInfo = self._anonymous_task_client.getTaskInfo(
            task_token)
        self.assertEqual(task_info.token, task_token)
        self.assertEqual(task_info.status,
                         TaskStatus._NAMES_TO_VALUES["RUNNING"])
        self.assertEqual(task_info.productId, 0)
        self.assertIsNone(task_info.actorUsername)
        self.assertIn("Dummy task", task_info.summary)
        self.assertEqual(task_info.cancelFlagSet, False)

        time.sleep(10)  # A bit more than exactly what remains of 10 seconds!
        task_info = self._anonymous_task_client.getTaskInfo(task_token)
        self.assertEqual(task_info.status,
                         TaskStatus._NAMES_TO_VALUES["COMPLETED"])
        self.assertEqual(task_info.cancelFlagSet, False)
        self.assertIsNotNone(task_info.enqueuedAtEpoch)
        self.assertIsNotNone(task_info.startedAtEpoch)
        self.assertLessEqual(task_info.enqueuedAtEpoch,
                             task_info.startedAtEpoch)
        self.assertIsNotNone(task_info.completedAtEpoch)
        self.assertLess(task_info.startedAtEpoch, task_info.completedAtEpoch)
        self.assertEqual(task_info.cancelFlagSet, False)

    def test_task_2_query_status_of_failed(self):
        task_token = self._anonymous_task_client.createDummyTask(10, True)

        time.sleep(5)
        task_info: TaskInfo = self._anonymous_task_client.getTaskInfo(
            task_token)
        self.assertEqual(task_info.token, task_token)
        self.assertEqual(task_info.status,
                         TaskStatus._NAMES_TO_VALUES["RUNNING"])
        self.assertEqual(task_info.cancelFlagSet, False)

        time.sleep(10)  # A bit more than exactly what remains of 10 seconds!
        task_info = self._anonymous_task_client.getTaskInfo(task_token)
        self.assertEqual(task_info.status,
                         TaskStatus._NAMES_TO_VALUES["FAILED"])
        self.assertEqual(task_info.cancelFlagSet, False)

    def test_task_3_cancel(self):
        task_token = self._anonymous_task_client.createDummyTask(10, False)

        time.sleep(3)
        cancel_req: bool = self._privileged_task_client.cancelTask(task_token)
        self.assertTrue(cancel_req)

        time.sleep(3)
        cancel_req_2: bool = self._privileged_task_client.cancelTask(
            task_token)
        # The task was already cancelled, so cancel_req_2 is not the API call
        # that cancelled the task.
        self.assertFalse(cancel_req_2)

        time.sleep(5)  # A bit more than exactly what remains of 10 seconds!
        task_info: TaskInfo = self._anonymous_task_client.getTaskInfo(
            task_token)
        self.assertEqual(task_info.status,
                         TaskStatus._NAMES_TO_VALUES["CANCELLED"])
        self.assertEqual(task_info.cancelFlagSet, True)
        self.assertIn("root", task_info.comments)
        self.assertIn("SUPERUSER requested cancellation.", task_info.comments)
        self.assertIn("CANCEL!\nCancel request of admin honoured by task.",
                      task_info.comments)
        self.assertIsNotNone(task_info.enqueuedAtEpoch)
        self.assertIsNotNone(task_info.startedAtEpoch)
        self.assertLessEqual(task_info.enqueuedAtEpoch,
                             task_info.startedAtEpoch)
        self.assertIsNotNone(task_info.completedAtEpoch)
        self.assertLess(task_info.startedAtEpoch, task_info.completedAtEpoch)

    def test_task_4_get_tasks_as_admin(self):
        with self.assertRaises(RequestFailed):
            self._admin_task_client.getTasks(TaskFilter(
                # No SUPERUSER rights of test admin.
                filterForNoProductID=True
            ))
        with self.assertRaises(RequestFailed):
            self._admin_task_client.getTasks(TaskFilter(
                # Default product, no PRODUCT_ADMIN rights of test admin.
                productIDs=[1]
            ))
        with self.assertRaises(RequestFailed):
            self._privileged_task_client.getTasks(TaskFilter(
                productIDs=[1],
                filterForNoProductID=True
            ))
        with self.assertRaises(RequestFailed):
            self._privileged_task_client.getTasks(TaskFilter(
                usernames=["foo", "bar"],
                filterForNoUsername=True
            ))

        # PRODUCT_ADMIN rights on test-specific product...
        task_infos: List[AdministratorTaskInfo] = \
            self._admin_task_client.getTasks(TaskFilter(productIDs=[2]))
        # ... but no product-specific tasks exist in this test suite.
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter())
        self.assertEqual(len(task_infos), 3)

        self.assertEqual(sum(1 for t in task_infos
                             if t.normalInfo.status ==
                             TaskStatus._NAMES_TO_VALUES["COMPLETED"]), 1)
        self.assertEqual(sum(1 for t in task_infos
                             if t.normalInfo.status ==
                             TaskStatus._NAMES_TO_VALUES["FAILED"]), 1)
        self.assertEqual(sum(1 for t in task_infos
                             if t.normalInfo.status ==
                             TaskStatus._NAMES_TO_VALUES["CANCELLED"]), 1)

    def test_task_5_info_query_filters(self):
        current_time_epoch = int(datetime.now(timezone.utc).timestamp())

        task_infos: List[AdministratorTaskInfo] = \
            self._privileged_task_client.getTasks(TaskFilter(
                machineIDs=["nonexistent"]
            ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            machineIDs=["unprivileged"]
        ))
        self.assertEqual(len(task_infos), 3)

        tokens_from_previous_test = [t.normalInfo.token for t in task_infos]

        task_infos = self._admin_task_client.getTasks(TaskFilter(
            tokens=tokens_from_previous_test
        ))
        # Admin client is not a SUPERUSER, it should not get the list of
        # tasks visible only to superusers because they are "server-level".
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            machineIDs=["privileged"]
        ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            startedBeforeEpoch=current_time_epoch
        ))
        self.assertEqual(len(task_infos), 3)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            startedAfterEpoch=current_time_epoch
        ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            cancelFlag=Ternary._NAMES_TO_VALUES["ON"]
        ))
        self.assertEqual(len(task_infos), 1)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            cancelFlag=Ternary._NAMES_TO_VALUES["OFF"]
        ))
        self.assertEqual(len(task_infos), 2)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            consumedFlag=Ternary._NAMES_TO_VALUES["ON"]
        ))
        self.assertEqual(len(task_infos), 3)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            consumedFlag=Ternary._NAMES_TO_VALUES["OFF"]
        ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter())

        current_time_epoch = int(datetime.now(timezone.utc).timestamp())
        for i in range(10):
            target_api = self._anonymous_task_client if i % 2 == 0 \
                else self._admin_task_client
            for j in range(10):
                target_api.createDummyTask(1, bool(j % 2 == 0))

        task_infos = self._privileged_task_client.getTasks(TaskFilter())
        self.assertEqual(len(task_infos), 103)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
        ))
        self.assertEqual(len(task_infos), 100)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            machineIDs=["unprivileged"]
        ))
        self.assertEqual(len(task_infos), 50)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            machineIDs=["privileged"]
        ))
        self.assertEqual(len(task_infos), 50)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            filterForNoUsername=True,
        ))
        self.assertEqual(len(task_infos), 50)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            usernames=["admin"],
        ))
        self.assertEqual(len(task_infos), 50)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            usernames=["root"],
        ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch
        ))
        # Some tasks ought to have started at least.
        self.assertGreater(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch,
            completedAfterEpoch=current_time_epoch
        ))
        # Some tasks ought to have also finished at least.
        self.assertGreater(len(task_infos), 0)

        # Let every task terminate. We should only need 1 second per task,
        # running likely in a multithreaded environment.
        # Let's have some leeway, though...
        time.sleep(2 * (100 * 1 // cast(int, os.cpu_count())))

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch,
            completedAfterEpoch=current_time_epoch
        ))
        # All tasks should have finished.
        self.assertEqual(len(task_infos), 100)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch,
            completedAfterEpoch=current_time_epoch,
            statuses=[TaskStatus._NAMES_TO_VALUES["COMPLETED"]]
        ))
        self.assertEqual(len(task_infos), 50)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch,
            completedAfterEpoch=current_time_epoch,
            statuses=[TaskStatus._NAMES_TO_VALUES["FAILED"]]
        ))
        self.assertEqual(len(task_infos), 50)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch,
            completedAfterEpoch=current_time_epoch,
            cancelFlag=Ternary._NAMES_TO_VALUES["ON"]
        ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch,
            completedAfterEpoch=current_time_epoch,
            consumedFlag=Ternary._NAMES_TO_VALUES["ON"]
        ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            machineIDs=["*privileged"]
        ))
        self.assertEqual(len(task_infos), 103)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            kinds=["*Dummy*"]
        ))
        self.assertEqual(len(task_infos), 103)

        # Try to consume the task status from the wrong user!
        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedAfterEpoch=current_time_epoch,
            completedAfterEpoch=current_time_epoch,
            filterForNoUsername=True,
            statuses=[TaskStatus._NAMES_TO_VALUES["COMPLETED"]]
        ))
        self.assertEqual(len(task_infos), 25)
        a_token: str = task_infos[0].normalInfo.token
        with self.assertRaises(RequestFailed):
            self._admin_task_client.getTaskInfo(a_token)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            machineIDs=["workspace-manager"]
        ))
        self.assertEqual(len(task_infos), 0)

    def test_task_6_dropping(self):
        current_time_epoch = int(datetime.now(timezone.utc).timestamp())
        many_task_count = 4 * cast(int, os.cpu_count())
        for _ in range(many_task_count):
            self._anonymous_task_client.createDummyTask(600, False)

        STOP_SERVER_NO_AUTH.set()
        time.sleep(30)
        STOP_SERVER_NO_AUTH.clear()
        after_shutdown_time_epoch = int(datetime.now(timezone.utc)
                                        .timestamp())

        task_infos: List[AdministratorTaskInfo] = \
            self._privileged_task_client.getTasks(TaskFilter(
                enqueuedAfterEpoch=current_time_epoch,
                statuses=[
                    TaskStatus._NAMES_TO_VALUES["ENQUEUED"],
                    TaskStatus._NAMES_TO_VALUES["RUNNING"],
                    TaskStatus._NAMES_TO_VALUES["COMPLETED"],
                    TaskStatus._NAMES_TO_VALUES["FAILED"],
                    TaskStatus._NAMES_TO_VALUES["CANCELLED"]
                ]
            ))
        self.assertEqual(len(task_infos), 0)

        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            statuses=[TaskStatus._NAMES_TO_VALUES["DROPPED"]],
            # System-level dropping is not a "cancellation" action!
            cancelFlag=Ternary._NAMES_TO_VALUES["OFF"]
        ))
        self.assertEqual(len(task_infos), many_task_count)
        dropped_task_infos = {ti.normalInfo.token: ti for ti in task_infos}

        # Some tasks will have started, and the server pulled out from under.
        task_infos = self._privileged_task_client.getTasks(TaskFilter(
            enqueuedAfterEpoch=current_time_epoch,
            startedBeforeEpoch=after_shutdown_time_epoch,
            statuses=[TaskStatus._NAMES_TO_VALUES["DROPPED"]]
        ))
        for ti in task_infos:
            self.assertIn("SHUTDOWN!\nTask honoured graceful cancel signal "
                          "generated by server shutdown.",
                          ti.normalInfo.comments)
            del dropped_task_infos[ti.normalInfo.token]

        # The rest could have never started.
        for ti in dropped_task_infos.values():
            self.assertTrue("DROPPED!\n" in ti.normalInfo.comments or
                            "SHUTDOWN!\n" in ti.normalInfo.comments)
