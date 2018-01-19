# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Provides a context manager over a database sessionmaker.
"""


class DBSession(object):
    """
    Requires a session maker object and creates one session which can be used
    in the context.

    The session will be automatically closed, but committing must be done
    inside the context.
    """
    def __init__(self, session_maker):
        self.__session = None
        self.__session_maker = session_maker

    def __enter__(self):
        # create new session
        self.__session = self.__session_maker()
        return self.__session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__session:
            self.__session.close()
