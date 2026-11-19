# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from datetime import datetime

import sqlalchemy

from codechecker_api.python.shared.ttypes import RequestFailed, ErrorCode

from codechecker_common.logger import get_logger


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


def datetime_to_api_str(dt: datetime | None) -> str | None:
    """
    Convert a datetime to the string sent over the API.

    Naive values, such as the ones stored in the database, are in the server's
    local timezone. The result always has microseconds and an explicit UTC
    offset, e.g. "2024-07-01 12:00:00.000000+02:00".
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.isoformat(sep=' ', timespec='microseconds')


def api_str_to_datetime(date_str: str) -> datetime:
    """
    Parse a date string received over the API into a naive datetime in the
    server's local timezone, so it can be compared with database values.

    Both the current format with a UTC offset and the old offset-less format
    (with or without microseconds) are accepted. Offset-less values are
    assumed to be in the server's local timezone.
    """
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt
