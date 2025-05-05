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

from codechecker_client.thrift_call import thrift_client_call
from .base import BaseClientHelper


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
class ThriftAuthHelper(BaseClientHelper):
    def __init__(self, protocol, host, port, uri, session_token=None):
        super().__init__(protocol, host, port, uri, session_token)

        self.client = codeCheckerAuthentication.Client(self.protocol)

    @thrift_client_call
    def checkAPIVersion(self):
        pass

    # ============= Authentication and session handling =============
    @thrift_client_call
    def getAuthParameters(self):
        pass

    @thrift_client_call
    def getAcceptedAuthMethods(self):
        pass

    @thrift_client_call
    def getAccessControl(self):
        pass

    @thrift_client_call
    def performLogin(self, auth_method, auth_string):
        pass

    @thrift_client_call
    def createLink(self, provider):
        pass

    @thrift_client_call
    def getOauthProviders(self):
        pass

    @thrift_client_call
    def destroySession(self):
        pass

    # ============= Authorization, permission management =============
    @thrift_client_call
    def getPermissions(self, scope):
        pass

    # pylint: disable=redefined-builtin
    @thrift_client_call
    def getPermissionsForUser(self, scope, extra_params, filter):
        pass

    @thrift_client_call
    def getAuthorisedNames(self, permission, extra_params):
        pass

    @thrift_client_call
    def addPermission(self, permission, auth_name, is_group, extra_params):
        pass

    @thrift_client_call
    def removePermission(self, permission, auth_name, is_group, extra_params):
        pass

    @thrift_client_call
    def hasPermission(self, permission, extra_params):
        pass

    # ============= Token management =============

    @thrift_client_call
    def newToken(self, description):
        pass

    @thrift_client_call
    def removeToken(self, token):
        pass

    @thrift_client_call
    def getTokens(self):
        pass

    @thrift_client_call
    def newPersonalAccessToken(self, name, description):
        pass

    @thrift_client_call
    def removePersonalAccessToken(self, name):
        pass

    @thrift_client_call
    def getPersonalAccessTokens(self):
        pass
