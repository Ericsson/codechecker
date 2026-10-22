# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Unit tests for resolving SQLite product database paths. """


import unittest

from codechecker_server.database.database import SQLServer


class SqliteRelativePathTest(unittest.TestCase):
    """
    Tests for SQLServer.resolve_sqlite_relative_path, which turns a
    workspace-relative SQLite connection string back into an absolute one
    at connect time (see #3081: product database paths used to be stored
    as absolute paths, breaking when the workspace directory was moved).
    """

    def test_resolves_relative_sqlite_path(self):
        connection_string = 'sqlite+pysqlite:///foo.sqlite'
        resolved = SQLServer.resolve_sqlite_relative_path(
            connection_string, '/work/cfg')
        self.assertEqual(resolved, 'sqlite+pysqlite:////work/cfg/foo.sqlite')

    def test_leaves_absolute_sqlite_path_unchanged(self):
        connection_string = 'sqlite+pysqlite:////abs/foo.sqlite'
        resolved = SQLServer.resolve_sqlite_relative_path(
            connection_string, '/work/cfg')
        self.assertEqual(resolved, connection_string)

    def test_leaves_postgresql_connection_unchanged(self):
        connection_string = \
            'postgresql+psycopg2://user:pass@host:5432/dbname'
        resolved = SQLServer.resolve_sqlite_relative_path(
            connection_string, '/work/cfg')
        self.assertEqual(resolved, connection_string)
