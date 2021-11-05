# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper for tha authentication api.
"""

from codechecker_api.Authentication_v6 import codeCheckerAuthentication

from codechecker_client.thrift_call import ThriftClientCall
from .base import BaseClientHelper


class ThriftAuthHelper(BaseClientHelper):
    def __init__(self, protocol, host, port, uri, session_token=None):
        super().__init__(protocol, host, port, uri, session_token)

        self.client = codeCheckerAuthentication.Client(self.protocol)

    @ThriftClientCall
    def checkAPIVersion(self):
        pass

    # ============= Authentication and session handling =============
    @ThriftClientCall
    def getAuthParameters(self):
        pass

    @ThriftClientCall
    def getAcceptedAuthMethods(self):
        pass

    @ThriftClientCall
    def getAccessControl(self):
        pass

    @ThriftClientCall
    def performLogin(self, auth_method, auth_string):
        pass

    @ThriftClientCall
    def destroySession(self):
        pass

    # ============= Authorization, permission management =============
    @ThriftClientCall
    def getPermissions(self, scope):
        pass

    @ThriftClientCall
    def getPermissionsForUser(self, scope, extra_params, filter):
        pass

    @ThriftClientCall
    def getAuthorisedNames(self, permission, extra_params):
        pass

    @ThriftClientCall
    def addPermission(self, permission, auth_name, is_group, extra_params):
        pass

    @ThriftClientCall
    def removePermission(self, permission, auth_name, is_group, extra_params):
        pass

    @ThriftClientCall
    def hasPermission(self, permission, extra_params):
        pass

    # ============= Token management =============

    @ThriftClientCall
    def newToken(self, description):
        pass

    @ThriftClientCall
    def removeToken(self, token):
        pass

    @ThriftClientCall
    def getTokens(self):
        pass
