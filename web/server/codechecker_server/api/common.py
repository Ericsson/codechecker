# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import functools

import sqlalchemy

import codechecker_api_shared
from codechecker_api_shared.ttypes import RequestFailed, ErrorCode

from codechecker_common.logger import get_logger
from codechecker_server import permissions
from codechecker_server.database.database import DBSession


LOG = get_logger("server")


def exc_to_thrift_reqfail(function):
    """
    Convert internal exceptions to a `RequestFailed` Thrift exception, which
    can be sent back to the RPC client.
    """
    func_name = function.__name__

    def wrapper(*args, **kwargs):
        try:
            res = function(*args, **kwargs)
            return res
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            # Convert SQLAlchemy exceptions.
            msg = str(alchemy_ex)
            import traceback
            traceback.print_exc()

            # pylint: disable=raise-missing-from
            raise RequestFailed(ErrorCode.DATABASE, msg)
        except RequestFailed as rf:
            LOG.warning("%s:\n%s", func_name, rf.message)
            raise
        except Exception as ex:
            import traceback
            traceback.print_exc()
            msg = str(ex)
            LOG.warning("%s:\n%s", func_name, msg)

            # pylint: disable=raise-missing-from
            raise RequestFailed(ErrorCode.GENERAL, msg)

    return wrapper


def __requires_permission(self, required):
    """
    Helper method to raise an UNAUTHORIZED exception if the user does not
    have any of the given permissions.
    """

    with DBSession(self._config_database) as session:
        args = dict({ 'productID': self._product.id })
        args['config_db_session'] = session

        if not any(permissions.require_permission(
                perm, args, self._auth_session,
                self._manager.is_enabled)
                for perm in required):
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                "You are not authorized to execute this action.")

        return True


def requires_permission(required):
    """
    Decorator for Thrift API methods that require one of the given permissions
    on the current product.
    """
    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, *args, **kwargs):
            __requires_permission(self, required)
            return function(self, *args, **kwargs)
        return wrapper
    return decorator


def requires_view(function):
    """
    Decorator for Thrift API methods that require view permission on the
    current product.
    """
    @functools.wraps(function)
    def wrapper(self, *args, **kwargs):
        __requires_permission(self, [
            permissions.PRODUCT_VIEW,
            permissions.PERMISSION_VIEW
        ])
        return function(self, *args, **kwargs)
    return wrapper


def requires_store(function):
    """
    Decorator for Thrift API methods that require store permission on the
    current product.
    """
    @functools.wraps(function)
    def wrapper(self, *args, **kwargs):
        __requires_permission(self, [permissions.PRODUCT_STORE])
        return function(self, *args, **kwargs)
    return wrapper


def requires_access(function):
    """
    Decorator for Thrift API methods that require access permission on the
    current product.
    """
    @functools.wraps(function)
    def wrapper(self, *args, **kwargs):
        __requires_permission(self, [permissions.PRODUCT_ACCESS])
        return function(self, *args, **kwargs)
    return wrapper


def requires_admin(function):
    """
    Decorator for Thrift API methods that require admin permission on the
    current product.
    """
    @functools.wraps(function)
    def wrapper(self, *args, **kwargs):
        __requires_permission(self, [permissions.PRODUCT_ADMIN])
        return function(self, *args, **kwargs)
    return wrapper
