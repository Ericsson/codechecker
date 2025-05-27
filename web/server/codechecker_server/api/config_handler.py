# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handle Thrift requests for configuration.
"""


import codechecker_api_shared

from codechecker_common.logger import get_logger

from codechecker_server.profiler import timeit

from codechecker_web.shared import convert

from ..database.config_db_model import Configuration
from ..database.database import DBSession

LOG = get_logger('server')


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
class ThriftConfigHandler:
    """
    Manages Thrift requests regarding configuration.
    """

    def __init__(self, auth_session, config_session, session_manager):
        self.__auth_session = auth_session
        self.__session = config_session
        self.__session_manager = session_manager

    def __require_supermission(self):
        """
        Checks if the current user isn't a SUPERUSER.
        """

        # Anonymous access is only allowed if authentication is
        # turned off
        if self.__session_manager.is_enabled and not self.__auth_session:
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                "You are not authorized to execute this action.")

        if (self.__auth_session is not None and
                not self.__auth_session.is_root):
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                "You are not authorized to modify the notification.")

        return True

    @timeit
    def getNotificationBannerText(self):
        """
        Retrieves the notification banner text.
        """

        notificationString = ''
        with DBSession(self.__session) as session:
            notificationQuery = session.query(Configuration) \
                .filter(
                    Configuration.config_key == 'notification_banner_text') \
                .one_or_none()

            if notificationQuery is not None:
                notificationString = notificationQuery.config_value

        return convert.to_b64(notificationString)

    @timeit
    def setNotificationBannerText(self, notification_b64):
        """
        Sets the notification banner remove_products_except.
        Beware: This method only works if the user is a SUPERUSER.
        """

        self.__require_supermission()

        notification = convert.from_b64(notification_b64)

        with DBSession(self.__session) as session:
            notificationQuery = session.query(Configuration) \
                .filter(
                    Configuration.config_key == 'notification_banner_text') \
                .one_or_none()

            if notificationQuery is None:
                conf = Configuration('notification_banner_text', notification)
                session.add(conf)
                session.flush()
            else:
                # update it
                notificationQuery.config_value = notification

            session.commit()
            session.close()
