# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handles the allocation and destruction of privileged sessions associated
with a particular CodeChecker server.
"""

import getpass
import hashlib
import json
import os
import portalocker
import stat
import shutil
import time
import tempfile
import uuid

from datetime import datetime

from codechecker_lib import logger

unsupported_methods = []

try:
    import ldap
except ImportError:
    unsupported_methods.append("ldap")

try:
    import pam
    import grp
    import pwd
except ImportError:
    unsupported_methods.append("pam")

LOG = logger.get_new_logger("SESSION MANAGER")
SESSION_COOKIE_NAME = "__ccPrivilegedAccessToken"
session_lifetimes = {}


# ------------------------------
# ----------- SERVER -----------
class _Session():
    """A session for an authenticated, privileged client connection."""

    # Create an initial salt from system environment for use with the session
    # permanent persistency routine.
    __initial_salt = hashlib.sha256(SESSION_COOKIE_NAME + "__" +
                                    str(time.time()) + "__" +
                                    os.urandom(16)).hexdigest()

    @staticmethod
    def calc_persistency_hash(client_addr, auth_string):
        """Calculates a more secure persistency hash for the session. This
        persistency hash is intended to be used for the "session recycle"
        feature to prevent NAT endpoints from accidentally getting each
        other's session."""
        return hashlib.sha256(auth_string + "@" + client_addr + ":" +
                              _Session.__initial_salt).hexdigest()

    def __init__(self, client_addr, token, phash):
        self.client = client_addr
        self.token = token
        self.persistent_hash = phash
        self.last_access = datetime.now()

    def still_valid(self, do_revalidate=False):
        """Returns if the session is still valid, and optionally revalidates
        it. A session is valid in its soft-lifetime."""
        if (datetime.now() - self.last_access).total_seconds() <= \
                session_lifetimes["soft"] \
                and (datetime.now() - self.last_access).total_seconds() <= \
                session_lifetimes["hard"]:
            # If the session is still valid within the "reuse enabled" (soft)
            # past and the check comes from a real user access, we revalidate
            # the session by extending its lifetime --- the user retains their
            # data.
            if do_revalidate:
                self.revalidate()

            # The session is still valid if it has been used in the past
            # (length of "past" is up to server host)
            return True

        # If the session is older than the "soft" limit,
        # the user needs to authenticate again.
        return False

    def still_reusable(self):
        """Returns whether the session is still reusable, ie. within its
        hard lifetime: while a session is reusable, a valid authentication
        from the session's user will return the user to the session."""
        return (datetime.now() - self.last_access).total_seconds() <= \
            session_lifetimes["hard"]

    def revalidate(self):
        if self.still_reusable():
            # A session is only revalidated if it has yet to exceed its
            # "hard" lifetime. After a session hasn't been used for this
            # timeframe, it can NOT be resurrected at all --- the user needs
            # to log in into a brand-new session.
            self.last_access = datetime.now()

class SessionManager:
    CodeChecker_Workspace = None

    __valid_sessions = []
    __logins_since_prune = 0

    def __init__(self):
        LOG.debug('Loading session config')

        # Check whether workspace's configuration exists.
        session_cfg_file = os.path.join(SessionManager.CodeChecker_Workspace,
                                        "session_config.json")
        if not os.path.exists(session_cfg_file):
            LOG.warning("CodeChecker server's authentication example "
                        "configuration file created at " + session_cfg_file)
            shutil.copyfile(os.path.join(os.environ['CC_PACKAGE_ROOT'],
                                         "config", "session_config.json"),
                            session_cfg_file)

        LOG.debug(session_cfg_file)

        scfg_dict = {'authentication': {'enabled': False}}
        with open(session_cfg_file, 'r') as scfg:
            scfg_dict.update(json.loads(scfg.read()))

        self.__auth_config = scfg_dict["authentication"]

        # If no methods are configured as enabled, disable authentication.
        if scfg_dict["authentication"].get("enabled"):
            found_auth_method = False

            if "method_dictionary" in self.__auth_config and \
                    self.__auth_config["method_dictionary"].get("enabled"):
                found_auth_method = True

            if "method_ldap" in self.__auth_config and \
                    self.__auth_config["method_ldap"].get("enabled"):
                if "ldap" not in unsupported_methods:
                    found_auth_method = True
                else:
                    LOG.warning("LDAP authentication was enabled but "
                                "prerequisites are NOT installed on the system"
                                "... Disabling LDAP authentication")
                    self.__auth_config["method_ldap"]["enabled"] = False

            if "method_pam" in self.__auth_config and \
                    self.__auth_config["method_pam"].get("enabled"):
                if "pam" not in unsupported_methods:
                    found_auth_method = True
                else:
                    LOG.warning("PAM authentication was enabled but "
                                "prerequisites are NOT installed on the system"
                                "... Disabling PAM authentication")
                    self.__auth_config["method_pam"]["enabled"] = False

            #
            if not found_auth_method:
                LOG.warning("Authentication is enabled but no valid "
                            "authentication backends are configured... "
                            "Falling back to no authentication.")
                self.__auth_config["enabled"] = False

        session_lifetimes["soft"] = self.__auth_config.get("soft_expire")\
            or 60
        session_lifetimes["hard"] = self.__auth_config.get("session_lifetime")\
            or 300

    def isEnabled(self):
        return self.__auth_config.get("enabled")

    def getRealm(self):
        return {
            "realm": self.__auth_config.get("realm_name"),
            "error": self.__auth_config.get("realm_error")
        }

    def __handle_validation(self, auth_string):
        """Validate an oncoming authorization request
        against some authority controller."""
        return self.__try_auth_dictionary(auth_string) \
            or self.__try_auth_pam(auth_string) \
            or self.__try_auth_ldap(auth_string)

    def __is_method_enabled(self, method):
        return method not in unsupported_methods and \
            "method_" + method in self.__auth_config and \
            self.__auth_config["method_" + method].get("enabled")

    def __try_auth_dictionary(self, auth_string):
        return self.__is_method_enabled("dictionary") and \
            auth_string in \
            self.__auth_config.get("method_dictionary").get("auths")

    def __try_auth_pam(self, auth_string):
        if self.__is_method_enabled("pam"):
            username, pw = auth_string.split(":")
            auth = pam.pam()

            if auth.authenticate(username, pw):
                allowed_users = self.__auth_config["method_pam"].get("users") \
                    or []
                allowed_group = self.__auth_config["method_pam"].get("groups")\
                    or []

                if len(allowed_users) == 0 and len(allowed_group) == 0:
                    # If no filters are set, only authentication is needed.
                    return True
                else:
                    if username in allowed_users:
                        # The user is allowed by username.
                        return True

                    # Otherwise, check group memeberships. If any of the user's
                    # groups are an allowed groupl, the user is allowed
                    groups = [g.gr_name for g in grp.getgrall()
                              if username in g.gr_mem]
                    gid = pwd.getpwnam(username).pw_gid
                    groups.append(grp.getgrgid(gid).gr_name)

                    return not set(groups).isdisjoint(
                        set(self.__auth_config["method_pam"].get("groups")))

        return False

    def __try_auth_ldap(self, auth_string):
        if self.__is_method_enabled("ldap"):
            username, pw = auth_string.split(":")
            for server in self.__auth_config["method_ldap"].get("authorities"):
                l = ldap.initialize(server["connection_url"])

                for query in server["queries"]:
                    try:
                        l.simple_bind_s(query.replace("$USN$", username), pw)
                        return True
                    except ldap.LDAPError as e:
                        toPrint = ''
                        if e.message:
                            if 'info' in e.message:
                                toPrint = toPrint + e.message['info']
                            if 'info' in e.message and 'desc' in e.message:
                                toPrint = toPrint + "; "
                            if 'desc' in e.message:
                                toPrint = toPrint + e.message['desc']
                        else:
                            toPrint = e.__repr__()

                        LOG.info("LDAP authentication error against " +
                                 server["connection_url"] + " with DN: " +
                                 query.replace("$USN$", username) + "\n" +
                                 "Error was: " + toPrint)
                    finally:
                        l.unbind()

        return False

    def create_or_get_session(self, client, auth_string):
        """Create a new session for the given client and auth-string, if
        it is valid. If an existing session is found, return that instead."""
        if not self.__auth_config["enabled"]:
            return None

        self.__logins_since_prune += 1
        if self.__logins_since_prune >= \
           self.__auth_config["logins_until_cleanup"]:
            self.__cleanup_sessions()

        if self.__handle_validation(auth_string):
            session_already = next(
                (s for s
                 in SessionManager.__valid_sessions if s.client == client
                 and s.still_reusable()
                 and s.persistent_hash ==
                 _Session.calc_persistency_hash(client, auth_string)),
                None)

            if session_already:
                session_already.revalidate()
                session = session_already
            else:
                # TODO: Use a more secure way for token generation?
                token = uuid.UUID(bytes=os.urandom(16)).__str__().replace("-",
                                                                          "")
                session = _Session(client, token,
                                   _Session.calc_persistency_hash(client,
                                                                  auth_string))
                SessionManager.__valid_sessions.append(session)

            return session.token
        else:
            return None

    def is_valid(self, client, token, access=False):
        """Validates a given token (cookie) against
        the known list of privileged sessions."""
        if not self.isEnabled():
            return True
        else:
            return any(_sess.client == client
                       and _sess.token == token
                       and _sess.still_valid(access)
                       for _sess in SessionManager.__valid_sessions)

    def invalidate(self, client, token):
        """Remove a user's previous session from the store."""
        for session in SessionManager.__valid_sessions[:]:
            if session.client == client and session.token == token:
                SessionManager.__valid_sessions.remove(session)
                return True

        return False

    def __cleanup_sessions(self):
        SessionManager.__valid_sessions = [s for s
                                           in SessionManager.__valid_sessions
                                           if s.still_reusable()]
        self.__logins_since_prune = 0


# ------------------------------
# ----------- CLIENT -----------
class SessionManager_Client:
    def __init__(self):
        LOG.debug('Loading session config')

        # Check whether user's configuration exists.
        session_cfg_file = os.path.join(os.path.expanduser("~"),
                                        ".codechecker_passwords.json")
        if not os.path.exists(session_cfg_file):
            LOG.info("CodeChecker authentication client's example "
                     "configuration file created at " + session_cfg_file)
            shutil.copyfile(os.path.join(os.environ['CC_PACKAGE_ROOT'],
                                         "config", "session_client.json"),
                            session_cfg_file)
            os.chmod(session_cfg_file, stat.S_IRUSR | stat.S_IWUSR)

        LOG.debug(session_cfg_file)
        with open(session_cfg_file, 'r') as scfg:
            scfg_dict = json.loads(scfg.read())

        if not scfg_dict["credentials"]:
            scfg_dict["credentials"] = {}

        self.__save = scfg_dict
        self.__autologin = scfg_dict.get("client_autologin") \
            if "client_autologin" in scfg_dict else True

        # Check and load token storage for user
        self.token_file = os.path.join(tempfile.gettempdir(), ".codechecker_" +
                                       getpass.getuser() + ".session.json")
        LOG.debug(self.token_file)
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                input = json.loads(f.read())
                self.__tokens = input.get("tokens")

            mode = os.stat(self.token_file)[stat.ST_MODE]
            if mode & stat.S_IRGRP \
                    or mode & stat.S_IWGRP \
                    or mode & stat.S_IROTH \
                    or mode & stat.S_IWOTH:
                LOG.warning("Credential file at '" + session_cfg_file + "' is "
                            "readable by users other than you! This poses a "
                            "risk of others getting your passwords!\n"
                            "Please `chmod 0600 " + session_cfg_file + "`")
        else:
            with open(self.token_file, 'w') as f:
                json.dump({'tokens': {}}, f)
            os.chmod(self.token_file, stat.S_IRUSR | stat.S_IWUSR)

            self.__tokens = {}

    def is_autologin_enabled(self):
        return self.__autologin

    def getToken(self, host, port):
        return self.__tokens.get(host + ":" + port)

    def getAuthString(self, host, port):
        ret = self.__save["credentials"].get(host + ":" + port)
        if not ret:
            ret = self.__save["credentials"].get(host)
        if not ret:
            ret = self.__save["credentials"].get("*:" + port)
        if not ret:
            ret = self.__save["credentials"].get("*")

        return ret

    def saveToken(self, host, port, token, destroy=False):
        if destroy:
            del self.__tokens[host + ":" + port]
        else:
            self.__tokens[host + ":" + port] = token

        with open(self.token_file, 'w') as scfg:
            portalocker.lock(scfg, portalocker.LOCK_EX)
            json.dump({'tokens': self.__tokens}, scfg,
                      indent=2, sort_keys=True)
            portalocker.unlock(scfg)
