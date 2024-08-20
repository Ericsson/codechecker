# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper for the "serverside tasks" Thrift API.
"""
from typing import Callable, List, Optional

from codechecker_api.codeCheckerServersideTasks_v6 import \
    codeCheckerServersideTaskService
from codechecker_api.codeCheckerServersideTasks_v6.ttypes import \
    AdministratorTaskInfo, TaskFilter, TaskInfo

from ..thrift_call import thrift_client_call
from .base import BaseClientHelper


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
class ThriftServersideTaskHelper(BaseClientHelper):
    """Clientside Thrift stub for the `codeCheckerServersideTaskService`."""

    def __init__(self, protocol: str, host: str, port: int, uri: str,
                 session_token: Optional[str] = None,
                 get_new_token: Optional[Callable] = None):
        super().__init__(protocol, host, port, uri,
                         session_token, get_new_token)

        self.client = codeCheckerServersideTaskService.Client(self.protocol)

    @thrift_client_call
    def getTaskInfo(self, _token: str) -> TaskInfo:
        raise NotImplementedError("Should have called Thrift code!")

    @thrift_client_call
    def getTasks(self, _filters: TaskFilter) -> List[AdministratorTaskInfo]:
        raise NotImplementedError("Should have called Thrift code!")

    @thrift_client_call
    def cancelTask(self, _token: str) -> bool:
        raise NotImplementedError("Should have called Thrift code!")

    @thrift_client_call
    def createDummyTask(self, _timeout: int, _should_fail: bool) -> str:
        raise NotImplementedError("Should have called Thrift code!")
