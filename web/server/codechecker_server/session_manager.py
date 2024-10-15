# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handles the management of authentication sessions on the server's side.
"""
import hashlib
import re

from datetime import datetime
from typing import Optional, Set

from codechecker_common.logger import get_logger
from codechecker_common.util import generate_random_token

from codechecker_web.shared.version import SESSION_COOKIE_NAME as _SCN

from .database.config_db_model import Session as SessionRecord
from .database.config_db_model import SystemPermission
from .permissions import SUPERUSER
from .server_configuration import Configuration


UNSUPPORTED_METHODS = []

try:
    from .auth import cc_ldap
except ImportError:
    UNSUPPORTED_METHODS.append("ldap")

try:
    from .auth import cc_pam
except ImportError:
    UNSUPPORTED_METHODS.append("pam")


LOG = get_logger("server")
SESSION_COOKIE_NAME = _SCN
SESSION_TOKEN_LENGTH = 32


class _Session:
    """A session for an authenticated, privileged client connection."""

    def __init__(self, token, username, groups,
                 session_lifetime, refresh_time, is_root=False, database=None,
                 last_access=None, can_expire=True):

        self.token = token
        self.user = username
        self.groups = groups

        self.session_lifetime = session_lifetime
        self.refresh_time = refresh_time
        self.__root = is_root
        self.__database = database
        self.__can_expire = can_expire
        self.last_access = last_access or datetime.now()

    @property
    def is_root(self):
        """Returns whether or not the Session was created with the master
        superuser (root) credentials."""
        return self.__root

    @property
    def is_refresh_time_expire(self):
        """
        Returns if the refresh time of the session is expired.
        """
        if not self.refresh_time:
            return True

        return (datetime.now() - self.last_access).total_seconds() > \
            self.refresh_time

    @property
    def is_alive(self):
        """
        Returns if the session is alive and usable, that is, within its
        lifetime.
        """
        if not self.__can_expire:
            return True

        return (datetime.now() - self.last_access).total_seconds() <= \
            self.session_lifetime

    def revalidate(self):
        """
        A session is only revalidated if it has yet to exceed its
        lifetime. After a session hasn't been used for this interval,
        it can NOT be resurrected at all --- the user needs to log in
        to a brand-new session.
        """

        if not self.is_alive:
            return

        if self.__database and self.is_refresh_time_expire:
            self.last_access = datetime.now()

            # Update the timestamp in the database for the session's last
            # access.
            transaction = None
            try:
                transaction = self.__database()
                record = transaction.query(SessionRecord) \
                    .filter(SessionRecord.user_name == self.user) \
                    .filter(SessionRecord.token == self.token) \
                    .limit(1).one_or_none()

                if record:
                    record.last_access = self.last_access
                    transaction.commit()
            except Exception as e:
                LOG.warning("Couldn't update usage timestamp of %s",
                            self.token)
                LOG.warning(str(e))
            finally:
                if transaction:
                    transaction.close()


class SessionManager:
    """
    Provides the functionality required to handle user authentication on a
    CodeChecker server.
    """

    def __init__(self,
                 configuration: Configuration,
                 root_sha: str,
                 force_auth: bool = False):
        """
        Initialise a new Session Manager on the server.

        :param configuration_file: The server's configuration data.
            It contains authentication backend configuration information.
        :param root_sha: The SHA-256 hash of the root user's authentication.
        :param force_auth: If True, the manager will be enabled even if the
            configuration file disables authentication.
        """
        self.__database_connection = None
        self.__logins_since_prune = 0
        self.__sessions = []
        self.__root_sha = root_sha
        self._configuration = configuration.authentication

        if force_auth:
            LOG.debug("Authentication was force-enabled.")
            self._configuration.enabled = True

        if not self.is_enabled:
            return

        # If no authentication methods are enabled, or none of them could
        # starts due to lack of valid configuration or lack of dependencies,
        # fall back to disabling authentication.
        found_working_auth_method = False
        if self._configuration.method_dictionary.enabled:
            found_working_auth_method = True

        if self._configuration.method_pam.enabled:
            if "pam" in UNSUPPORTED_METHODS:
                LOG.warning("PAM authentication was enabled but "
                            "prerequisites are NOT installed on the system"
                            "... Disabling PAM authentication.")
                self._configuration.method_pam.enabled = False
            else:
                found_working_auth_method = True

        if self._configuration.method_ldap.enabled:
            if "ldap" in UNSUPPORTED_METHODS:
                LOG.warning("LDAP authentication was enabled but "
                            "prerequisites are NOT installed on the system"
                            "... Disabling LDAP authentication.")
                self._configuration.method_ldap.enabled = False
            else:
                found_working_auth_method = True

        if not found_working_auth_method:
            if force_auth:
                LOG.warning("Authentication was force-enabled, but no "
                            "valid authentication backends are "
                            "configured... The server will only allow "
                            "the master superuser (\"root\") access.")
            else:
                LOG.warning("Authentication is enabled but no valid "
                            "authentication backends are configured... "
                            "Falling back to no authentication!")
                self._configuration.enabled = False

        # Pre-compile the regular expressions from 'regex_groups'.
        if self.is_enabled and self._configuration.regex_groups.enabled:
            self.__regex_groups = {g: [re.compile(rx) for rx in l]
                                   for g, l in self._configuration
                                   .regex_groups.groups.items()
                                   }
        else:
            self.__regex_groups = {}

    def configuration_reloaded_update_sessions(self):
        LOG.info("Updating lifetime of existing sessions ...")
        for session in self.__sessions:
            session.session_lifetime = self._configuration.session_lifetime
            session.refresh_time = self._configuration.refresh_time

    @property
    def is_enabled(self) -> bool:
        return self._configuration.enabled

    @property
    def default_superuser_name(self) -> Optional[str]:
        """Get default superuser name."""
        root = self.__root_sha.split(':', 1)

        # Previously, the root file doesn't contain the user name. In this case
        # we will return with no user name.
        if len(root) <= 1:
            return None

        return root[0]

    def set_database_connection(self, connection):
        """
        Set the instance's database connection to use in fetching
        database-stored sessions to the given connection.

        Use None as connection's value to unset the database.
        """
        self.__database_connection = connection

    def __handle_validation(self, auth_string: str) -> dict:
        """
        Validate an oncoming authorization request against some authority
        controller.

        Returns `False` if no validation was done, or a validation object if
        the user was successfully authenticated.

        This validation object contains two keys: username and groups.
        """
        validation = self.__try_auth_root(auth_string) \
            or self.__try_auth_dictionary(auth_string) \
            or self.__try_auth_pam(auth_string) \
            or self.__try_auth_ldap(auth_string)
        if not validation:
            return {}

        # If a validation method is enabled and regex_groups is enabled too,
        # we will extend the "groups".
        extra_groups = self.__try_regex_groups(validation["username"])
        if extra_groups:
            validation["groups"] = sorted(set(validation.get("groups", []))
                                          | extra_groups)

        LOG.debug("User validation details: %s", str(validation))
        return validation

    def __is_method_enabled(self, method: str) -> bool:
        return method not in UNSUPPORTED_METHODS and \
            getattr(self._configuration, f"method_{method}").enabled

    def __try_auth_root(self, auth_string: str) -> dict:
        """
        Try to authenticate the user against the root username:password's hash.
        """
        user_name = SessionManager.get_user_name(auth_string)
        sha = hashlib.sha256(auth_string.encode("utf-8")).hexdigest()

        if self.__root_sha == f"{user_name}:{sha}":
            return {"username": user_name,
                    "groups": [],
                    "root": True
                    }

        return {}

    def __try_auth_token(self, auth_string: str) -> dict:
        if not self.__database_connection:
            return {}

        user_name, token = auth_string.split(':', 1)

        transaction = None
        try:
            # Try the database, if it is connected.
            transaction = self.__database_connection()
            auth_session = transaction.query(SessionRecord.token) \
                .filter(SessionRecord.user_name == user_name) \
                .filter(SessionRecord.token == token) \
                .filter(SessionRecord.can_expire.is_(False)) \
                .limit(1).one_or_none()

            if not auth_session:
                return {}

            return auth_session
        except Exception as e:
            LOG.error("Couldn't check login in the database: %s", str(e))
        finally:
            if transaction:
                transaction.close()

        return {}

    def __try_auth_dictionary(self, auth_string: str) -> dict:
        """
        Try to authenticate the user against the hardcoded credential list.

        Returns a validation object if successful, which contains the users'
        groups.
        """
        if not self.__is_method_enabled("dictionary") or \
                auth_string not in self._configuration \
                .method_dictionary.auths:
            return {}

        username = SessionManager.get_user_name(auth_string)
        return {"username": username,
                "groups": self._configuration.method_dictionary
                .groups.get(username, [])
                }

    def __try_auth_pam(self, auth_string: str) -> dict:
        """
        Try to authenticate user based on the PAM configuration.
        """
        if not self.__is_method_enabled("pam"):
            return {}

        username, password = auth_string.split(':', 1)
        if cc_pam.auth_user(self._configuration.method_pam,
                            username, password):
            # PAM does not hold a group membership list we can reliably query.
            return {"username": username}

        return {}

    def __try_auth_ldap(self, auth_string: str) -> dict:
        """
        Try to authenticate user to all the configured authorities.
        """
        if self.__is_method_enabled("ldap"):
            username, password = auth_string.split(':', 1)
            for ldap_conf in self._configuration.method_ldap.authorities:
                if cc_ldap.auth_user(ldap_conf, username, password):
                    groups = cc_ldap.get_groups(ldap_conf, username, password)
                    self.__update_groups(username, groups)
                    return {"username": username,
                            "groups": groups}

        return {}

    def __update_groups(self, user_name, groups):
        """
        Updates group field of the users tokens.
        """
        if not self.__database_connection:
            return None

        transaction = None
        try:
            # Try the database, if it is connected.
            transaction = self.__database_connection()
            transaction.query(SessionRecord) \
                .filter(SessionRecord.user_name == user_name) \
                .update({SessionRecord.groups: ';'.join(groups)})
            transaction.commit()
            return True
        except Exception as e:
            LOG.error("Couldn't check login in the database: ")
            LOG.error(str(e))
        finally:
            if transaction:
                transaction.close()

        return False

    def __try_regex_groups(self, username) -> Set[str]:
        """
        Returns a set of groups that the user belongs to, depending on whether
        the username matches a regular expression of the group.
        """
        return {group
                for group, regexes in self.__regex_groups.items()
                for regex in regexes
                if re.search(regex, username)}

    @staticmethod
    def get_user_name(auth_string):
        return auth_string.split(':', 1)[0]

    def get_db_auth_session_tokens(self, user_name):
        """
        Get authentication session token from the database for the given user.
        """
        if not self.__database_connection:
            return None

        transaction = None
        try:
            # Try the database, if it is connected.
            transaction = self.__database_connection()
            session_tokens = transaction.query(SessionRecord) \
                .filter(SessionRecord.user_name == user_name) \
                .filter(SessionRecord.can_expire.is_(True)) \
                .all()
            return session_tokens
        except Exception as e:
            LOG.error("Couldn't check login in the database: ")
            LOG.error(str(e))
        finally:
            if transaction:
                transaction.close()

        return None

    def __is_root_user(self, user_name: str) -> bool:
        """ Return True if the given user has system permissions. """
        if self.default_superuser_name == user_name:
            return True

        transaction = None
        try:
            # Try the database, if it is connected.
            transaction = self.__database_connection()
            system_permission = transaction.query(SystemPermission) \
                .filter(SystemPermission.name == user_name) \
                .filter(SystemPermission.permission == SUPERUSER.name) \
                .limit(1).one_or_none()
            return bool(system_permission)
        except Exception as e:
            LOG.error("Couldn't get system permission from database: ")
            LOG.error(str(e))
        finally:
            if transaction:
                transaction.close()

        return False

    def __create_local_session(self, token, user_name, groups, is_root,
                               last_access=None, can_expire=True):
        """
        Returns a new local session object initalized by the given parameters.
        """
        if not is_root:
            is_root = self.__is_root_user(user_name)

        return _Session(
            token, user_name, groups,
            self._configuration.session_lifetime,
            self._configuration.refresh_time,
            is_root, self.__database_connection, last_access, can_expire)

    def create_session(self, auth_string):
        """Creates a new session for the given auth-string."""
        if not self.is_enabled:
            return None

        # Perform cleanup of session memory, if neccessary.
        self.__logins_since_prune += 1
        if self.__logins_since_prune >= \
                self._configuration.logins_until_cleanup:
            self.__cleanup_sessions()

        # Try authenticate user with personal access token.
        auth_token = self.__try_auth_token(auth_string)
        if auth_token:
            local_session = self.__get_local_session_from_db(auth_token.token)
            local_session.revalidate()
            self.__sessions.append(local_session)
            return local_session

        # Try to authenticate user with different authentication methods.
        validation = self.__handle_validation(auth_string)
        if not validation:
            return False

        # Generate a new token and create a local session.
        token = generate_random_token(SESSION_TOKEN_LENGTH)
        user_name = validation.get('username')
        groups = validation.get('groups', [])
        is_root = validation.get('root', False)

        local_session = self.__create_local_session(token, user_name,
                                                    groups, is_root)
        self.__sessions.append(local_session)

        # Store the session in the database.
        transaction = None
        if self.__database_connection:
            try:
                transaction = self.__database_connection()
                record = SessionRecord(token, user_name, ';'.join(groups))
                transaction.add(record)
                transaction.commit()
            except Exception as e:
                LOG.error("Couldn't store or update login record in "
                          "database:")
                LOG.error(str(e))
            finally:
                if transaction:
                    transaction.close()

        return local_session

    def __get_local_session_from_db(self, token):
        """
        Creates a local session if a valid session token can be found in the
        database.
        """

        if not self.__database_connection:
            return None

        transaction = None
        try:
            transaction = self.__database_connection()
            db_record = transaction.query(SessionRecord) \
                .filter(SessionRecord.token == token) \
                .limit(1).one_or_none()

            if db_record:
                user_name = db_record.user_name
                is_root = self.__is_root_user(user_name)

                groups = db_record.groups.split(';') \
                    if db_record.groups else []

                return self.__create_local_session(token, user_name,
                                                   groups,
                                                   is_root,
                                                   db_record.last_access,
                                                   db_record.can_expire)
        except Exception as e:
            LOG.error("Couldn't check login in the database: ")
            LOG.error(str(e))
        finally:
            if transaction:
                transaction.close()

        return None

    def get_session(self, token):
        """
        Retrieves the session for the given session cookie token from the
        server's memory backend, if such session exists or creates and returns
        a new one if the token exists in the database.

        :returns: The session object if one was found. None if authentication
        is not enabled, or if the cookie is not valid anymore.
        """

        if not self.is_enabled:
            return None

        for sess in self.__sessions:
            if sess.is_alive and sess.token == token:
                # If the session is alive but the should be re-validated.
                if sess.is_refresh_time_expire:
                    sess.revalidate()
                return sess

        # Try to get a local session from the database.
        local_session = self.__get_local_session_from_db(token)
        if local_session and local_session.is_alive:
            self.__sessions.append(local_session)
            if local_session.is_refresh_time_expire:
                local_session.revalidate()
            return local_session

        self.invalidate(token)

        return None

    def invalidate_local_session(self, token):
        """
        Remove a user's previous session from the local in memory store.
        """
        for session in self.__sessions[:]:
            if session.token == token:
                self.__sessions.remove(session)
                return True
        return False

    def invalidate(self, token):
        """
        Remove a user's previous session from local in memory and the database
        store.
        """
        transaction = None
        try:
            self.invalidate_local_session(token)

            transaction = self.__database_connection() \
                if self.__database_connection else None

            # Remove sessions from the database.
            if transaction:
                transaction.query(SessionRecord) \
                    .filter(SessionRecord.token == token) \
                    .filter(SessionRecord.can_expire.is_(True)) \
                    .delete()
                transaction.commit()

            return True
        except Exception as e:
            LOG.error("Couldn't invalidate session for token %s", token)
            LOG.error(str(e))
        finally:
            if transaction:
                transaction.close()

        return False

    def __cleanup_sessions(self):
        self.__logins_since_prune = 0

        for s in self.__sessions:
            if s.is_refresh_time_expire:
                self.invalidate_local_session(s.token)

        for s in self.__sessions:
            if not s.is_alive:
                self.invalidate(s.token)
