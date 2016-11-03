# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
Handle thrift requests for authentication
'''
import zlib
import os
import datetime
from collections import defaultdict
import ntpath
import codecs


import shared
from Authentication import constants
from Authentication.ttypes import *

from codechecker_lib import logger
from codechecker_lib import session_manager

LOG = logger.get_new_logger('AUTH HANDLER')


# -----------------------------------------------------------------------
def timefunc(function):
    '''
    timer function
    '''

    func_name = function.__name__

    def debug_wrapper(*args, **kwargs):
        '''
        wrapper for debug log
        '''
        before = datetime.now()
        res = function(*args, **kwargs)
        after = datetime.now()
        timediff = after - before
        diff = timediff.microseconds/1000
        LOG.debug('['+str(diff)+'ms] ' + func_name)
        return res

    def release_wrapper(*args, **kwargs):
        '''
        no logging
        '''
        res = function(*args, **kwargs)
        return res

    if logger.get_log_level() == logger.DEBUG:
        return debug_wrapper
    else:
        return release_wrapper


def conv(text):
    '''
    Convert * to % got from clients for the database queries.
    '''
    if text is None:
        return '%'
    return text.replace('*', '%')


class ThriftAuthHandler():
    '''
    Handle Thrift authentication requests.
    '''

    def __init__(self, manager, client_host, session_token=None):
        self.__manager = manager
        self.__client_host = client_host
        self.__session_token = session_token

    @timefunc
    def getAuthParameters(self):
        return HandshakeInformation(self.__manager.isEnabled(),
                                    self.__manager.is_valid(
                                        self.__client_host,
                                        self.__session_token,
                                        True))

    @timefunc
    def getAcceptedAuthMethods(self):
        result = []
        result.append("Username:Password")
        return result

    @timefunc
    def performLogin(self, auth_method, auth_string):
        if auth_method == "Username:Password":
            authToken = self.__manager.create_or_get_session(
                self.__client_host,
                auth_string)
            if authToken:
                return authToken
            else:
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.PRIVILEGE,
                    "Invalid credentials supplied. Refusing authentication!")

        raise shared.ttypes.RequestFailed(
            shared.ttypes.ErrorCode.PRIVILEGE,
            "Could not negotiate via common authentication method.")

    @timefunc
    def destroySession(self):
        return self.__manager.invalidate(self.__client_host,
                                         self.__session_token)
