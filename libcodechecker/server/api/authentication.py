# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests for authentication.
"""

import json

import sqlalchemy

import shared
from Authentication_v6.ttypes import *

from libcodechecker.logger import get_logger
from libcodechecker.profiler import timeit
from libcodechecker.server import permissions
from libcodechecker.server.permissions \
    import handler_from_scope_params as make_handler
from libcodechecker.server.permissions \
    import require_manager, require_permission

LOG = get_logger('server')


class ThriftAuthHandler(object):
    """
    Handle Thrift authentication requests.
    """

    def __init__(self, manager, auth_session, config_database):
        self.__manager = manager
        self.__auth_session = auth_session
        self.__config_db = config_database

    @timeit
    def checkAPIVersion(self):
        # This is a deliberate empty call which if succeeds, marks for the
        # client that the server accepted the connection proper.
        pass

    # ============= Authentication and session handling =============

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
                    shared.ttypes.ErrorCode.AUTH_DENIED,
                    "Invalid credentials supplied. Refusing authentication!")

        raise shared.ttypes.RequestFailed(
            shared.ttypes.ErrorCode.AUTH_DENIED,
            "Could not negotiate via common authentication method.")

    @timeit
    def destroySession(self):
        token = None
        if self.__auth_session:
            token = self.__auth_session.token
        return self.__manager.invalidate(token)

    # ============= Authorization, permission management =============

    @staticmethod
    def __unpack_extra_params(extra_params, session=None):
        """
        Helper function to unpack the extra_params JSON string to a dict.

        If specified, add the config_db_session to this dict too.
        """

        if extra_params and extra_params != "":
            params = json.loads(extra_params)
        else:
            params = {}

        if session:
            params['config_db_session'] = session

        return params

    @staticmethod
    def __create_permission_args(perm_enum, extra_params_string, session):
        """
        Helper function to transform the permission-specific values from the
        API into the appropriate Python constructs needed by the permission
        library.
        """

        perm = permissions.permission_from_api_enum(perm_enum)
        params = ThriftAuthHandler.__unpack_extra_params(extra_params_string,
                                                         session)
        return perm, params

    @timeit
    def getPermissions(self, scope):
        """
        Returns all the defined permissions in the given permission scope.
        """

        return [permissions.api_enum_for_permission(p)
                for p in permissions.get_permissions(scope)]

    @timeit
    def getPermissionsForUser(self, scope, extra_params, perm_filter):
        """
        Returns the permissions in the given permission scope and with the
        given scope-specific extra_params for the current logged in user,
        based on the permission filters.

        Filters in the perm_filter struct are joined in an AND clause.
        """

        if perm_filter is None or not any(perm_filter.__dict__.values()):
            # If no filtering is needed, this function behaves identically
            # to getPermissions().
            return self.getPermissions(scope)

        try:
            session = self.__config_db()

            # The database connection must always be passed to the permission
            # handler.
            params = ThriftAuthHandler.__unpack_extra_params(extra_params,
                                                             session)

            perms = []
            for perm in permissions.get_permissions(scope):
                should_return = True
                handler = make_handler(perm, params)

                if should_return and perm_filter.given:
                    should_return = handler.has_permission(self.__auth_session)

                if should_return and perm_filter.canManage:
                    # If the user has any of the permissions that are
                    # authorised to manage the currently iterated permission,
                    # the filter passes.
                    should_return = require_manager(
                         perm, params, self.__auth_session)

                if should_return:
                    perms.append(perm)

            return [permissions.api_enum_for_permission(p)
                    for p in perms]

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def getAuthorisedNames(self, permission, extra_params):
        """
        Returns the users and groups who were EXPLICITLY granted a particular
        permission.
        """

        try:
            session = self.__config_db()
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            if not require_manager(perm, params, self.__auth_session):
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You can not manage the permission '{0}'"
                    .format(perm.name))

            handler = make_handler(perm, params)
            users, groups = handler.list_permitted()

            # The special default permission marker is an internal value.
            users = filter(lambda user: user != '*', users)

            return AuthorisationList(users, groups)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def addPermission(self, permission, auth_name, is_group, extra_params):
        """
        Adds the given permission to the user or group named auth_name.
        """

        try:
            session = self.__config_db()
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            if not require_manager(perm, params, self.__auth_session):
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You can not manage the permission '{0}'"
                    .format(perm.name))

            handler = make_handler(perm, params)
            handler.add_permission(auth_name, is_group)

            session.commit()
            return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def removePermission(self, permission, auth_name, is_group, extra_params):
        """
        Removes the given permission from the user or group auth_name.
        """

        try:
            session = self.__config_db()
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            if not require_manager(perm, params, self.__auth_session):
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You can not manage the permission '{0}'"
                    .format(perm.name))

            handler = make_handler(perm, params)
            handler.remove_permission(auth_name, is_group)

            session.commit()
            return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def hasPermission(self, permission, extra_params):
        """
        Returns whether or not the current logged-in user (or guest, if
        authentication is disabled) is granted the given permission.

        This method observes permission inheritance.
        """

        try:
            session = self.__config_db()
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            return require_permission(perm, params,
                                      self.__auth_session)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()
