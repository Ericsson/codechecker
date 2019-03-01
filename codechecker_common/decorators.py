# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Various decorators.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import sqlalchemy

import shared


def catch_sqlalchemy(method):
    def wrapped(*args, **kw):
        try:
            return method(*args, **kw)
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    return wrapped
