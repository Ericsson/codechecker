# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handles the allocation and destruction of privileged sessions associated
with a particular CodeChecker server.
"""

from datetime import datetime
import getpass
import hashlib
import json
import os
import shutil
import stat
import time
import uuid

import portalocker

from libcodechecker.logger import LoggerFactory

unsupported_methods = []

try:
    from libcodechecker.libauth import cc_ldap
except ImportError:
    unsupported_methods.append("ldap")

try:
    from libcodechecker.libauth import cc_pam
except ImportError:
    unsupported_methods.append("pam")

LOG = LoggerFactory.get_new_logger("SESSION MANAGER")
SESSION_COOKIE_NAME = "__ccPrivilegedAccessToken"
session_lifetimes = {}


class _Session(object):
    """A session for an authenticated, privileged client connection."""

    # Create an initial salt from system environment for use with the session
    # permanent persistency routine.
    __initial_salt = hashlib.sha256(SESSION_COOKIE_NAME + "__" +
                                    str(time.time()) + "__" +
                                    os.urandom(16)).hexdigest()

    @staticmethod
    def calc_persistency_hash(auth_string):
        """Calculates a more secure persistency hash for the session. This
        persistency hash is intended to be used for the "session recycle"
        feature to prevent NAT endpoints from accidentally getting each
        other's session."""
        return hashlib.sha256(auth_string + "@" +
                              _Session.__initial_salt).hexdigest()

    def __init__(self, token, phash, username, groups, is_root=False):
        self.last_access = datetime.now()
        self.token = token
        self.persistent_hash = phash
        self.user = username
        self.groups = groups

        self.__root = is_root

    @property
    def is_root(self):
        """Returns whether or not the Session was created with the master
        superuser (root) credentials."""
        return self.__root

    def still_valid(self, do_revalidate=False):
        """Returns if the session is still valid, and optionally revalidates
        it. A session is valid in its soft-lifetime."""

        if (datetime.now() - self.last_access).total_seconds() <= \
                session_lifetimes["soft"] and self.still_reusable():
            # If the session is still valid within the "reuse enabled" (soft)
            # past and the check comes from a real user access, we revalidate
            # the session by extending its lifetime --- the user retains their
            # data.
            if do_revalidate:
                self.revalidate()

            # The session is still valid if it has been used in the past
            # (length of "past" is up to server host).
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


def check_file_owner_rw(file_to_check):
    """
    Check the file permissions.
    Return:
        True if only the owner can read or write the file.
        False if other users or groups can read or write the file.
    """

    mode = os.stat(file_to_check)[stat.ST_MODE]
    if mode & stat.S_IRGRP \
            or mode & stat.S_IWGRP \
            or mode & stat.S_IROTH \
            or mode & stat.S_IWOTH:
        LOG.warning("'{0}' is readable by users other than you!"
                    " This poses a risk of leaking sensitive"
                    " information, such as passwords, session tokens, etc.!\n"
                    "Please 'chmod 0600 {0}' so only you can access the file."
                    .format(file_to_check))
        return False
    return True


def load_session_cfg(session_cfg_file):
    """
    Tries to load the session config file which should be a
    valid json file, if loading fails returns an empty dict.
    """

    scfg_dict = {}
    try:
        with open(session_cfg_file, 'r') as scfg:
            scfg_dict = json.loads(scfg.read())
        check_file_owner_rw(session_cfg_file)

    except IOError:
        LOG.debug('Failed to open user authentication file: ' +
                  session_cfg_file)
    except ValueError as verr:
        LOG.warning(verr)
        LOG.warning('Not valid user authentication file: ' +
                    session_cfg_file)

    return scfg_dict


class SessionManager:
    CodeChecker_Workspace = None

    __valid_sessions = []
    __logins_since_prune = 0

    def __init__(self, root_sha, force_auth=False):
        LOG.debug('Loading session config')

        # Check whether workspace's configuration exists.
        session_cfg_file = os.path.join(SessionManager.CodeChecker_Workspace,
                                        "session_config.json")

        if not os.path.exists(session_cfg_file):
            LOG.info("CodeChecker server's authentication example "
                     "configuration file created at " + session_cfg_file)
            shutil.copyfile(os.path.join(os.environ['CC_PACKAGE_ROOT'],
                                         "config", "session_config.json"),
                            session_cfg_file)

        LOG.debug(session_cfg_file)

        # Create the default settings and then load the file from the disk.
        scfg_dict = {'authentication': {'enabled': False}}
        scfg_dict.update(load_session_cfg(session_cfg_file))

        self.__auth_config = scfg_dict["authentication"]

        if force_auth:
            LOG.debug("Authentication was force-enabled.")
            self.__auth_config['enabled'] = True

        # Save the root SHA into the configuration (but only in memory!)
        self.__auth_config['method_root'] = root_sha

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
                                "... Disabling LDAP authentication.")
                    self.__auth_config["method_ldap"]["enabled"] = False

            if "method_pam" in self.__auth_config and \
                    self.__auth_config["method_pam"].get("enabled"):
                if "pam" not in unsupported_methods:
                    found_auth_method = True
                else:
                    LOG.warning("PAM authentication was enabled but "
                                "prerequisites are NOT installed on the system"
                                "... Disabling PAM authentication.")
                    self.__auth_config["method_pam"]["enabled"] = False

            #
            if not found_auth_method:
                if force_auth:
                    LOG.warning("Authentication was manually enabled, but no "
                                "valid authentication backends are "
                                "configured... The server will only allow "
                                "the master superuser (root) access.")
                else:
                    LOG.warning("Authentication is enabled but no valid "
                                "authentication backends are configured... "
                                "Falling back to no authentication.")
                    self.__auth_config["enabled"] = False

        session_lifetimes["soft"] = \
            self.__auth_config.get("soft_expire") or 60
        session_lifetimes["hard"] = \
            self.__auth_config.get("session_lifetime") or 300

    def isEnabled(self):
        return self.__auth_config.get("enabled")

    def getRealm(self):
        return {
            "realm": self.__auth_config.get("realm_name"),
            "error": self.__auth_config.get("realm_error")
        }

    def __handle_validation(self, auth_string):
        """
        Validate an oncoming authorization request
        against some authority controller.

        Returns False if no validation was done, or a validation object
        if the user was successfully authenticated.

        This validation object contains two keys: username and groups.
        """
        validation = self.__try_auth_dictionary(auth_string)
        if validation:
            return validation

        validation = self.__try_auth_pam(auth_string)
        if validation:
            return validation

        validation = self.__try_auth_ldap(auth_string)
        if validation:
            return validation

        return False

    def __is_method_enabled(self, method):
        return method not in unsupported_methods and \
            "method_" + method in self.__auth_config and \
            self.__auth_config["method_" + method].get("enabled")

    def __try_auth_root(self, auth_string):
        """
        Try to authenticate the user against the root username:password's hash.
        """
        if "method_root" in self.__auth_config and \
                hashlib.sha256(auth_string).hexdigest() == \
                self.__auth_config["method_root"]:
            return {
                'username': SessionManager.get_user_name(auth_string),
                'groups': [],
                'root': True
            }

        return False

    def __try_auth_dictionary(self, auth_string):
        """
        Try to authenticate the user against the hardcoded credential list.

        Returns a validation object if successful, which contains the users'
        groups.
        """
        method_config = self.__auth_config.get("method_dictionary")
        if not method_config:
            return False

        valid = self.__is_method_enabled("dictionary") and \
            auth_string in method_config.get("auths")
        if not valid:
            return False

        username = SessionManager.get_user_name(auth_string)
        group_list = method_config['groups'][username] if \
            'groups' in method_config and \
            username in method_config['groups'] else []

        return {
            'username': username,
            'groups': group_list
        }

    def __try_auth_pam(self, auth_string):
        """
        Try to authenticate user based on the PAM configuration.
        """
        if self.__is_method_enabled("pam"):
            username, password = auth_string.split(":")
            if cc_pam.auth_user(self.__auth_config["method_pam"],
                                username, password):
                # PAM does not hold a group membership list we can reliably
                # query.
                return {'username': username}

        return False

    def __try_auth_ldap(self, auth_string):
        """
        Try to authenticate user to all the configured authorities.
        """
        if self.__is_method_enabled("ldap"):
            username, password = auth_string.split(":")

            ldap_authorities = self.__auth_config["method_ldap"] \
                .get("authorities")
            for ldap_conf in ldap_authorities:
                if cc_ldap.auth_user(ldap_conf, username, password):
                    # TODO: Fetch the LDAP groups of user.
                    return {'username': username, 'groups': []}

        return False

    @staticmethod
    def get_user_name(auth_string):
        return auth_string.split(":")[0]

    def create_or_get_session(self, auth_string):
        """Create a new session for the given auth-string, if it is valid. If
        an existing session is found, return that instead.
        Currently only username:password format auth_string
        is supported.
        """
        if not self.__auth_config["enabled"]:
            return None

        self.__logins_since_prune += 1
        if self.__logins_since_prune >= \
                self.__auth_config["logins_until_cleanup"]:
            self.__cleanup_sessions()

        validation = self.__try_auth_root(auth_string)
        if not validation:
            validation = self.__handle_validation(auth_string)

        if validation:
            # If the session is still valid and credentials
            # are resent return old token.
            session_already = next(
                (s for s
                 in SessionManager.__valid_sessions if s.still_reusable() and
                 s.persistent_hash ==
                    _Session.calc_persistency_hash(auth_string)),
                None)

            if session_already:
                session_already.revalidate()
                session = session_already
            else:
                # TODO: Use a more secure way for token generation?
                token = uuid.UUID(bytes=os.urandom(16)).__str__().replace("-",
                                                                          "")

                user_name = validation['username']
                groups = validation.get("groups", [])
                is_root = validation.get('root', False)

                session = _Session(token,
                                   _Session.calc_persistency_hash(auth_string),
                                   user_name, groups, is_root)
                SessionManager.__valid_sessions.append(session)

            return session

        return None

    def is_valid(self, token, access=False):
        """Validates a given token (cookie) against
        the known list of privileged sessions."""
        if not self.isEnabled():
            return True
        else:
            return any(_sess.token == token and _sess.still_valid(access)
                       for _sess in SessionManager.__valid_sessions)

    def get_session(self, token, access=False):
        """Gets the privileged session object based
        based on the token.
        """
        if not self.isEnabled():
            return None
        for _sess in SessionManager.__valid_sessions:
            if _sess.token == token and _sess.still_valid(access):
                return _sess
        return None

    def invalidate(self, token):
        """Remove a user's previous session from the store."""
        for session in SessionManager.__valid_sessions[:]:
            if session.token == token:
                SessionManager.__valid_sessions.remove(session)
                return True

        return False

    def __cleanup_sessions(self):
        SessionManager.__valid_sessions = [s for s
                                           in SessionManager.__valid_sessions
                                           if s.still_reusable()]
        self.__logins_since_prune = 0


class SessionManager_Client:
    def __init__(self):
        LOG.debug('Loading session config')

        # Check whether user's configuration exists.
        user_home = os.path.expanduser("~")
        session_cfg_file = os.path.join(user_home,
                                        ".codechecker.passwords.json")
        LOG.debug(session_cfg_file)

        if not os.path.exists(session_cfg_file):
            # Filenames were different pre-5.8.
            old_file = os.path.join(user_home, ".codechecker_passwords.json")
            if os.path.exists(old_file):
                shutil.move(old_file, session_cfg_file)

        scfg_dict = load_session_cfg(session_cfg_file)

        if not scfg_dict.get("credentials"):
            scfg_dict["credentials"] = {}

        self.__save = scfg_dict
        self.__autologin = scfg_dict.get("client_autologin") \
            if "client_autologin" in scfg_dict else True

        # Check and load token storage for user
        self.token_file = os.path.join(user_home, ".codechecker.session.json")
        LOG.debug(self.token_file)

        if not os.path.exists(self.token_file):
            # Filenames were different pre-5.8.
            old_file = os.path.join(user_home,
                                    ".codechecker_{0}.session.json".format(
                                        getpass.getuser()
                                    ))
            if os.path.exists(old_file):
                shutil.move(old_file, self.token_file)

        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                input = json.loads(f.read())
                self.__tokens = input.get("tokens")
            check_file_owner_rw(self.token_file)
        else:
            with open(self.token_file, 'w') as f:
                json.dump({'tokens': {}}, f)
            os.chmod(self.token_file, stat.S_IRUSR | stat.S_IWUSR)

            self.__tokens = {}

    def is_autologin_enabled(self):
        return self.__autologin

    def getToken(self, host, port):
        return self.__tokens.get("{0}:{1}".format(host, port))

    def getAuthString(self, host, port):
        ret = self.__save["credentials"].get("{0}:{1}".format(host, port))
        if not ret:
            ret = self.__save["credentials"].get(host)
        if not ret:
            ret = self.__save["credentials"].get("*:{0}".format(port))
        if not ret:
            ret = self.__save["credentials"].get("*")

        return ret

    def saveToken(self, host, port, token, destroy=False):
        if destroy:
            del self.__tokens["{0}:{1}".format(host, port)]
        else:
            self.__tokens["{0}:{1}".format(host, port)] = token

        with open(self.token_file, 'w') as scfg:
            portalocker.lock(scfg, portalocker.LOCK_EX)
            json.dump({'tokens': self.__tokens}, scfg,
                      indent=2, sort_keys=True)
            portalocker.unlock(scfg)
