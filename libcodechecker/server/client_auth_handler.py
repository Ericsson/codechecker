# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests for authentication.
"""

import shared
from Authentication.ttypes import *

from libcodechecker.logger import LoggerFactory
from libcodechecker.profiler import timeit

LOG = LoggerFactory.get_new_logger('AUTH HANDLER')


def conv(text):
    """
    Convert * to % got from clients for the database queries.
    """
    if text is None:
        return '%'
    return text.replace('*', '%')


class ThriftAuthHandler(object):
    """
    Handle Thrift authentication requests.
    """

    def __init__(self, manager, auth_session):
        self.__manager = manager
        self.__auth_session = auth_session

    @timeit
    def getAuthParameters(self):
        token = None
        if self.__auth_session:
            token = self.__auth_session.token
        return HandshakeInformation(self.__manager.isEnabled(),
                                    self.__manager.is_valid(
                                        token,
                                        True))

    @timeit
    def getLoggedInUser(self):
        if self.__auth_session:
            return self.__auth_session.user
        else:
            return ""

    @timeit
    def getAcceptedAuthMethods(self):
        return ["Username:Password"]

    @timeit
    def performLogin(self, auth_method, auth_string):
        if auth_method == "Username:Password":
            session = self.__manager.create_or_get_session(auth_string)

            if session:
                return session.token
            else:
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.PRIVILEGE,
                    "Invalid credentials supplied. Refusing authentication!")

        raise shared.ttypes.RequestFailed(
            shared.ttypes.ErrorCode.PRIVILEGE,
            "Could not negotiate via common authentication method.")

    @timeit
    def destroySession(self):
        token = None
        if self.__auth_session:
            token = self.__auth_session.token
        return self.__manager.invalidate(token)
