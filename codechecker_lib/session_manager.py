# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
Handles the allocation and destruction of privileged sessions associated
with a particular CodeChecker server.
'''

import os
import uuid
import json

from codechecker_lib import logger

LOG = logger.get_new_logger("SESSION MANAGER")

session_cookie_name = "__ccPrivilegedAccessToken"


# ----------- SERVER -----------

class sessionManager:
    valid_sessions = []

    @staticmethod
    def validate(sessToken):
        sessionManager.valid_sessions.append(sessToken)

    @staticmethod
    def invalidate(sessToken):
        if sessToken in sessionManager.valid_sessions:
            sessionManager.valid_sessions.remove(sessToken)

    @staticmethod
    def isValid(sessToken):
        if not sessionManager().isEnabled():
            # If authentication is disabled, any kind of session token is valid.
            return True

        return sessToken in sessionManager.valid_sessions

    def __init__(self):
        LOG.debug('Loading session config')

        session_cfg_file = os.path.join(os.environ['CC_PACKAGE_ROOT'], "config", "session_config.json")
        LOG.debug(session_cfg_file)
        with open(session_cfg_file, 'r') as scfg:
            scfg_dict = json.loads(scfg.read())

        if not scfg_dict["authentication"]:
            scfg_dict["authentication"] = {'enabled': False}

        self.__auth_config = scfg_dict["authentication"]
        print self

    def isEnabled(self):
        return self.__auth_config.get("enabled")



def validate_session_token(token):
    '''Validates a given token (cookie) against the known list of privileged sessions'''
    return sessionManager.isValid(token)

def validate_auth_request(authString):
    '''Validate an oncoming authorization request against some authority controller'''
    return authString == "cc:valid"

def create_session():
    # TODO: More secure way for token generation?
    token = uuid.UUID(bytes = os.urandom(16)).__str__()
    sessionManager.validate(token)

    return token

# ----------- CLIENT -----------
class sessionManager_Client:
    def __init__(self):
        LOG.debug('Loading session config')

        session_cfg_file = os.path.join(os.environ['CC_PACKAGE_ROOT'], "config", "session_config.json")
        LOG.debug(session_cfg_file)
        with open(session_cfg_file, 'r') as scfg:
            scfg_dict = json.loads(scfg.read())

        if not scfg_dict["credentials"]:
            scfg_dict["credentials"] = {}
        if not scfg_dict["tokens"]:
            scfg_dict["tokens"] = {}

        self.__save = scfg_dict
        self.__autologin = scfg_dict["authentication"].get("client_autologin") if "client_autologin" in scfg_dict["authentication"] else True
        print self

    def is_autologin_enabled(self):
        return self.__autologin

    def getToken(self, host, port):
        return self.__save["tokens"].get(host + ":" + port)

    def getAuthString(self, host, port):
        ret = self.__save["credentials"].get(host + ":" + port)
        if not ret:
            ret = self.__save["credentials"].get(host)
            if not ret:
                ret = self.__save["credentials"].get("*:" + port)
                if not ret:
                    ret = self.__save["credentials"].get("*")

        return ret

    def saveToken(self, host, port, token, destroy = False):
        if not destroy:
            self.__save["tokens"][host + ":" + port] = token
        else:
            del self.__save["tokens"][host + ":" + port]

        session_cfg_file = os.path.join(os.environ['CC_PACKAGE_ROOT'], "config", "session_config.json")
        with open(session_cfg_file, 'w') as scfg:
            json.dump(self.__save, scfg, indent = 2, sort_keys = True)