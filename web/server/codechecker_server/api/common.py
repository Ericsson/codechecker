# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import sqlalchemy

from codechecker_api_shared.ttypes import RequestFailed, ErrorCode

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
