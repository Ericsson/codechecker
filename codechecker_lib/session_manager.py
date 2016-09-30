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
import hashlib
import time

from codechecker_lib import logger

LOG = logger.get_new_logger("SESSION MANAGER")

session_cookie_name = "__ccPrivilegedAccessToken"


# ----------- SERVER -----------

class _Session():
    # Create an initial salt from system environment for use with the session permanent persistency routine
    __initial_salt = hashlib.sha256(session_cookie_name + "__" + str(time.time()) + "__" + os.urandom(16)).hexdigest()

    @staticmethod
    def calc_persistency_hash(client_addr, auth_string):
        '''Calculates a more secure persistency hash for the session. This persistency hash is intended to be used
        for the "session recycle" feature to prevent NAT endpoints from accidentally getting each other's session.'''
        return hashlib.sha256(auth_string + "@" + client_addr + ":" + _Session.__initial_salt).hexdigest()

    def __init__(self, client_addr, token, phash):
        self.client = client_addr
        self.token = token
        self.persistent_hash = phash



    def still_valid(self):
        # TODO: This.
        return True

    def revalidate(self):
        # TODO: This
        return self.still_valid()

class sessionManager:
    __valid_sessions = []

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

    def getRealm(self):
        return { "realm": self.__auth_config.get("realm_name"), "error": self.__auth_config.get("realm_error"), "cookie": session_cookie_name }

    def __handle_validation(self, auth_string):
        '''Validate an oncoming authorization request against some authority controller'''
        # TODO: This
        return True

    def create_or_get_session(self, client, auth_string):
        '''Create a new session for the given client and auth-string, if it is valid.
        If an existing session is found, return that instead.'''
        if self.__handle_validation(auth_string):
            session_already = next((s for s in sessionManager.__valid_sessions if s.client == client
                                                                               and s.still_valid()
                                                                               and s.persistent_hash ==
                                                                                     _Session.calc_persistency_hash(client, auth_string)
                              ), None)

            if session_already:
                session_already.revalidate()
                session = session_already
            else:
                # TODO: More secure way for token generation?
                token = uuid.UUID(bytes=os.urandom(16)).__str__()
                session = _Session(client, token, _Session.calc_persistency_hash(client, auth_string))
                sessionManager.__valid_sessions.append(session)

            return session.token
        else:
            return None

    def is_valid(self, client, token):
        '''Validates a given token (cookie) against the known list of privileged sessions'''
        if not self.isEnabled():
            return True
        else:
            return any(_sess.client == client
                         and _sess.token == token
                         and _sess.still_valid()
                       for _sess in sessionManager.__valid_sessions)

    def invalidate(self, client, token):
        '''Remove a user's previous session from the store'''
        for session in sessionManager.__valid_sessions[:]:
            if session.client == client and session.token == token:
                sessionManager.__valid_sessions.remove(session)
                return True

        return False


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