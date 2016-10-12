# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import time

import shared
import sqlalchemy


def timeit(method):
    def timed(*args, **kw):
        timer_begin = time.time()
        result = method(*args, **kw)
        timer_end = time.time()

        print('%r (%r, %r) %2.2f sec' % (method.__name__, args, kw,
                                         timer_end - timer_begin))
        return result

    return timed


def trace(method):
    def wrapped(*args, **kw):
        print('Stepped into ' + method.__name__)
        result = method(*args, **kw)

        print('Stepped out ' + method.__name__)
        return result

    return wrapped


def catch_sqlalchemy(method):
    def wrapped(*args, **kw):
        try:
            return method(*args, **kw)
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    return wrapped
