# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol
from thrift.protocol.TProtocol import TProtocolException
from thrift.Thrift import TApplicationException

from Authentication_v6 import codeCheckerAuthentication

from libcodechecker import util
from libcodechecker.libclient.thrift_call import ThriftClientCall
from libcodechecker.logger import get_logger

from credential_manager import SESSION_COOKIE_NAME

LOG = get_logger('system')


class ThriftAuthHelper():
    def __init__(self, protocol, host, port, uri,
                 session_token=None):
        self.__host = host
        self.__port = port
        url = util.create_product_url(protocol, host, port, uri)
        self.transport = THttpClient.THttpClient(url)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = codeCheckerAuthentication.Client(self.protocol)

        if session_token:
            headers = {'Cookie': SESSION_COOKIE_NAME + '=' + session_token}
            self.transport.setCustomHeaders(headers)

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
