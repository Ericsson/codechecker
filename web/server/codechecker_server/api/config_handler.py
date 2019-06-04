# --------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests for configuration.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import base64

import shared

from codechecker_common.logger import get_logger
from codechecker_common.profiler import timeit

from ..database.config_db_model import Configuration
from .db import DBSession

LOG = get_logger('server')


class ThriftConfigHandler(object):
    """
    Manages Thrift requests regarding configuration.
    """

    def __init__(self, auth_session, config_session):
        self.__auth_session = auth_session
        self.__session = config_session

    def __require_supermission(self):
        """
        Checks if the current user isn't a SUPERUSER.
        """
        if (not (self.__auth_session is None) and
                not self.__auth_session.is_root):
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.UNAUTHORIZED,
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

        return base64.b64encode(notificationString.encode('utf-8'))

    @timeit
    def setNotificationBannerText(self, notification_b64):
        """
        Sets the notification banner remove_products_except.
        Bevare: This method only works if the use is a SUPERUSER.
        """

        self.__require_supermission()

        notification = base64.b64decode(notification_b64).decode('utf-8')

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
