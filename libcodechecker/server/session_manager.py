# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handles the management of authentication sessions on the server's side.
"""

from datetime import datetime
import hashlib
import os
import uuid

from sqlalchemy import and_

from libcodechecker.logger import get_logger
from libcodechecker.util import check_file_owner_rw
from libcodechecker.util import load_json_or_empty
from libcodechecker.version import SESSION_COOKIE_NAME as _SCN

from database.config_db_model import Session as SessionRecord

UNSUPPORTED_METHODS = []

try:
    from libcodechecker.libauth import cc_ldap
except ImportError:
    UNSUPPORTED_METHODS.append('ldap')

try:
    from libcodechecker.libauth import cc_pam
except ImportError:
    UNSUPPORTED_METHODS.append('pam')


LOG = get_logger("server")
SESSION_COOKIE_NAME = _SCN


class _Session(object):
    """A session for an authenticated, privileged client connection."""

    @staticmethod
    def calc_persistency_hash(auth_string, salt=None):
        """Calculates a more secure persistency hash for the session. This
        persistency hash is intended to be used for the "session recycle"
        feature to prevent NAT endpoints from accidentally getting each
        other's session."""
        return hashlib.sha256(auth_string + '@' +
                              salt if salt else 'CodeChecker').hexdigest()

    def __init__(self, token, phash, username, groups,
                 is_root=False, database=None):
        self.last_access = datetime.now()
        self.token = token
        self.persistent_hash = phash
        self.user = username
        self.groups = groups
        self.__root = is_root
        self.__database = database

    @property
    def is_root(self):
        """Returns whether or not the Session was created with the master
        superuser (root) credentials."""
        return self.__root

    def still_valid(self, soft_lifetime, hard_lifetime, do_revalidate=False):
        """
        Returns if the session is still valid, and optionally revalidates
        it. A session is valid in its soft-lifetime.
        """

        if (datetime.now() - self.last_access).total_seconds() <= \
                soft_lifetime and self.still_reusable(hard_lifetime):
            # If the session is still valid within the "reuse enabled" (soft)
            # past and the check comes from a real user access, we revalidate
            # the session by extending its lifetime --- the user retains their
            # data.
            if do_revalidate:
                self.revalidate(soft_lifetime, hard_lifetime)

            # The session is still valid if it has been used in the past
            # (length of "past" is up to server host).
            return True

        # If the session is older than the "soft" limit,
        # the user needs to authenticate again.
        return False

    def still_reusable(self, hard_lifetime):
        """Returns whether the session is still reusable, ie. within its
        hard lifetime: while a session is reusable, a valid authentication
        from the session's user will return the user to the session."""
        return (datetime.now() - self.last_access).total_seconds() <= \
            hard_lifetime

    def revalidate(self, soft_lifetime, hard_lifetime):
        if self.still_reusable(hard_lifetime):
            # A session is only revalidated if it has yet to exceed its
            # "hard" lifetime. After a session hasn't been used for this
            # timeframe, it can NOT be resurrected at all --- the user needs
            # to log in into a brand-new session.
            self.last_access = datetime.now()

            if self.__database and not self.still_reusable(soft_lifetime):
                # Update the timestamp in the database for the session's last
                # access. We only do this if the soft-lifetime has expired so
                # that not EVERY API requests' EVERY session check creates a
                # database write.
                try:
                    transaction = self.__database()
                    record = transaction.query(SessionRecord). \
                        get(self.persistent_hash)

                    if record:
                        record.last_access = self.last_access
                        transaction.commit()
                except Exception as e:
                    LOG.error("Couldn't update usage timestamp of {0}"
                              .format(self.token))
                    LOG.error(str(e))
                finally:
                    transaction.close()


class SessionManager:
    """
    Provides the functionality required to handle user authentication on a
    CodeChecker server.
    """

    def __init__(self, configuration_file, session_salt,
                 root_sha, force_auth=False):
        """
        Initialise a new Session Manager on the server.

        :param configuration_file: The configuration file to read
            authentication backends from.
        :param session_salt: An initial salt that will be used in hashing
            the session to the database.
        :param root_sha: The SHA-256 hash of the root user's authentication.
        :param force_auth: If True, the manager will be enabled even if the
            configuration file disables authentication.
        """
        self.__database_connection = None
        self.__logins_since_prune = 0
        self.__sessions = []
        self.__session_salt = hashlib.sha1(session_salt).hexdigest()

        LOG.debug(configuration_file)
        scfg_dict = load_json_or_empty(configuration_file, {},
                                       'server configuration')
        if scfg_dict != {}:
            check_file_owner_rw(configuration_file)
        else:
            # If the configuration dict is empty, it means a JSON couldn't
            # have been parsed from it.
            raise ValueError("Server configuration file was invalid, or "
                             "empty.")

        self.__max_run_count = scfg_dict['max_run_count'] \
            if 'max_run_count' in scfg_dict else None

        self.__auth_config = scfg_dict['authentication']

        if force_auth:
            LOG.debug("Authentication was force-enabled.")
            self.__auth_config['enabled'] = True

        # Save the root SHA into the configuration (but only in memory!)
        self.__auth_config['method_root'] = root_sha

        # If no methods are configured as enabled, disable authentication.
        if scfg_dict['authentication'].get('enabled'):
            found_auth_method = False

            if 'method_dictionary' in self.__auth_config and \
                    self.__auth_config['method_dictionary'].get('enabled'):
                found_auth_method = True

            if 'method_ldap' in self.__auth_config and \
                    self.__auth_config['method_ldap'].get('enabled'):
                if 'ldap' not in UNSUPPORTED_METHODS:
                    found_auth_method = True
                else:
                    LOG.warning("LDAP authentication was enabled but "
                                "prerequisites are NOT installed on the system"
                                "... Disabling LDAP authentication.")
                    self.__auth_config['method_ldap']['enabled'] = False

            if 'method_pam' in self.__auth_config and \
                    self.__auth_config['method_pam'].get('enabled'):
                if 'pam' not in UNSUPPORTED_METHODS:
                    found_auth_method = True
                else:
                    LOG.warning("PAM authentication was enabled but "
                                "prerequisites are NOT installed on the system"
                                "... Disabling PAM authentication.")
                    self.__auth_config['method_pam']['enabled'] = False

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
                    self.__auth_config['enabled'] = False

    @property
    def is_enabled(self):
        return self.__auth_config.get('enabled')

    def get_realm(self):
        return {
            "realm": self.__auth_config.get('realm_name'),
            "error": self.__auth_config.get('realm_error')
        }

    def set_database_connection(self, connection):
        """
        Set the instance's database connection to use in fetching
        database-stored sessions to the given connection.

        Use None as connection's value to unset the database.
        """
        self.__database_connection = connection

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
        return method not in UNSUPPORTED_METHODS and \
            'method_' + method in self.__auth_config and \
            self.__auth_config['method_' + method].get('enabled')

    def __try_auth_root(self, auth_string):
        """
        Try to authenticate the user against the root username:password's hash.
        """
        if 'method_root' in self.__auth_config and \
                hashlib.sha256(auth_string).hexdigest() == \
                self.__auth_config['method_root']:
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
        method_config = self.__auth_config.get('method_dictionary')
        if not method_config:
            return False

        valid = self.__is_method_enabled('dictionary') and \
            auth_string in method_config.get('auths')
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
        if self.__is_method_enabled('pam'):
            username, password = auth_string.split(':')
            if cc_pam.auth_user(self.__auth_config['method_pam'],
                                username, password):
                # PAM does not hold a group membership list we can reliably
                # query.
                return {'username': username}

        return False

    def __try_auth_ldap(self, auth_string):
        """
        Try to authenticate user to all the configured authorities.
        """
        if self.__is_method_enabled('ldap'):
            username, password = auth_string.split(':')

            ldap_authorities = self.__auth_config['method_ldap'] \
                .get('authorities')
            for ldap_conf in ldap_authorities:
                if cc_ldap.auth_user(ldap_conf, username, password):
                    groups = cc_ldap.get_groups(ldap_conf, username, password)
                    return {'username': username, 'groups': groups}

        return False

    @staticmethod
    def get_user_name(auth_string):
        return auth_string.split(':')[0]

    def _fetch_session_or_token(self, persistency_hash):
        """
        Contact the session store to try fetching a valid session or token
        for the given session object hash. This first uses the instance's
        in-memory storage, and if nothing is found, contacts the database
        (if connected).

        Returns a _Session object if found locally.
        Returns a string token if it was found in the database.
        None if a session wasn't found.
        """

        # Try the local store first.
        sessions = (s for s in self.__sessions
                    if self.__still_reusable(s) and
                    s.persistent_hash == persistency_hash)
        session = next(sessions, None)

        if not session and self.__database_connection:
            try:
                # Try the database, if it is connected.
                transaction = self.__database_connection()
                db_record = transaction.query(SessionRecord) \
                    .get(persistency_hash)

                if db_record:
                    if (datetime.now() - db_record.last_access). \
                            total_seconds() <= \
                            self.__auth_config['session_lifetime']:
                        # If a token was found in the database and the session
                        # for it can still be resurrected, we reuse this token.
                        return db_record.token
                    else:
                        # The token has expired, remove it from the database.
                        transaction.delete(db_record)
                        transaction.commit()
            except Exception as e:
                LOG.error("Couldn't check login in the database: ")
                LOG.error(str(e))
            finally:
                if transaction:
                    transaction.close()

        return session

    def create_or_get_session(self, auth_string):
        """Create a new session for the given auth-string, if it is valid. If
        an existing session is found, return that instead.
        Currently only username:password format auth_string
        is supported.
        """
        if not self.__auth_config['enabled']:
            return None

        self.__logins_since_prune += 1
        if self.__logins_since_prune >= \
                self.__auth_config['logins_until_cleanup']:
            self.__cleanup_sessions()

        validation = self.__try_auth_root(auth_string)
        if not validation:
            validation = self.__handle_validation(auth_string)

        if validation:
            sess_hash = _Session.calc_persistency_hash(self.__session_salt,
                                                       auth_string)
            local_session, db_token = None, None

            # If the session is still valid and credentials are resent,
            # return old token. This is fetched either locally or from the db.
            session_or_token = self._fetch_session_or_token(sess_hash)
            if session_or_token:
                if isinstance(session_or_token, _Session):
                    # We were able to fetch a session from the local in-memory
                    # storage.
                    local_session = session_or_token
                    self.__still_valid(local_session, do_revalidate=True)
                elif isinstance(session_or_token, basestring):
                    # The database gave us a token, which we will reuse in
                    # creating a local cache entry for the session.
                    db_token = session_or_token

            if not local_session:
                # If there isn't a Session locally, create it.
                token = db_token if db_token else \
                    uuid.UUID(bytes=os.urandom(16)).__str__().replace('-', '')

                user_name = validation['username']
                groups = validation.get('groups', [])
                is_root = validation.get('root', False)

                local_session = _Session(token, sess_hash,
                                         user_name, groups, is_root,
                                         self.__database_connection)
                self.__sessions.append(local_session)

                if self.__database_connection:
                    if not db_token:
                        # If db_token is None, the session was created
                        # brand new.
                        try:
                            transaction = self.__database_connection()
                            record = SessionRecord(sess_hash, token)
                            transaction.add(record)
                            transaction.commit()
                        except Exception as e:
                            LOG.error("Couldn't store login into database: ")
                            LOG.error(str(e))
                        finally:
                            if transaction:
                                transaction.close()
                    else:
                        # The local session was created from a token
                        # already present in the database, thus we can't
                        # add a new one.
                        self.__still_valid(local_session, do_revalidate=True)

            return local_session

    def is_valid(self, token, access=False):
        """Validates a given token (cookie) against
        the known list of privileged sessions."""
        if not self.is_enabled:
            return True

        return any(sess.token == token and self.__still_valid(sess, access)
                   for sess in self.__sessions)

    def get_max_run_count(self):
        """
        Returns the maximum storable run count. If the value is None it means
        we can upload unlimited number of runs.
        """
        return self.__max_run_count

    def get_session(self, token, access=False):
        """Gets the privileged session object based
        based on the token.
        """
        if not self.is_enabled:
            return None

        for sess in self.__sessions:
            if sess.token == token and self.__still_valid(sess, access):
                return sess

    def invalidate(self, token):
        """
        Remove a user's previous session from the store.
        """

        try:
            transaction = self.__database_connection() \
                if self.__database_connection else None

            for session in self.__sessions[:]:
                if session.token == token:
                    self.__sessions.remove(session)

                    if transaction:
                        transaction.query(SessionRecord). \
                            filter(and_(SessionRecord.auth_string ==
                                        session.persistent_hash,
                                        SessionRecord.token == token)). \
                            delete()
                        transaction.commit()

            return True
        except Exception as e:
            LOG.error("Couldn't invalidate session for token {0}"
                      .format(token))
            LOG.error(str(e))
        finally:
            if transaction:
                transaction.close()

        return False

    def __cleanup_sessions(self):
        tokens = [s.token for s in self.__sessions
                  if not self.__still_reusable(s)]
        self.__logins_since_prune = 0

        for token in tokens:
            self.invalidate(token)

    def __still_reusable(self, session):
        """
        Helper function for checking if the session could be
        resurrected, even if the soft grace period has expired.
        """
        return session.still_reusable(self.__auth_config['session_lifetime'])

    def __still_valid(self, session, do_revalidate=False):
        """
        Helper function for checking the validity of a session and
        optionally resurrecting it (if possible). This function uses the
        current instance's grace periods.
        """
        return session.still_valid(self.__auth_config['soft_expire'],
                                   self.__auth_config['session_lifetime'],
                                   do_revalidate)
