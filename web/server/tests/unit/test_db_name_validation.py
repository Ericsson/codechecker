# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Unit tests for the PostgreSQL database name validator. """


import unittest

from codechecker_common.util import is_valid_postgresql_db_name


class PostgresqlDbNameValidationTest(unittest.TestCase):
    """
    Tests for is_valid_postgresql_db_name, which guards against dangerous
    or unusable PostgreSQL database names before CodeChecker issues a
    CREATE DATABASE statement.
    """

    def test_accepts_plain_names(self):
        """Names that are legal even as unquoted identifiers are allowed."""
        self.assertTrue(is_valid_postgresql_db_name('myapp'))
        self.assertTrue(is_valid_postgresql_db_name('codechecker_test'))
        self.assertTrue(is_valid_postgresql_db_name('db2'))
        self.assertTrue(is_valid_postgresql_db_name('_internal'))

    def test_accepts_names_needing_quoting(self):
        """
        Names that are legal only as quoted identifiers are allowed, since
        CodeChecker always quotes the identifier when creating the database.
        These are the cases reported in the bug ticket.
        """
        self.assertTrue(is_valid_postgresql_db_name('test-product'))
        self.assertTrue(is_valid_postgresql_db_name('1team'))
        self.assertTrue(is_valid_postgresql_db_name('my-app-prod'))
        # "user" is a PostgreSQL reserved word but valid when quoted.
        self.assertTrue(is_valid_postgresql_db_name('user'))

    def test_rejects_empty_or_none(self):
        """Empty string and non-string inputs are rejected."""
        self.assertFalse(is_valid_postgresql_db_name(''))
        self.assertFalse(is_valid_postgresql_db_name(None))
        self.assertFalse(is_valid_postgresql_db_name(123))

    def test_rejects_dangerous_characters(self):
        """
        Characters that could break out of a quoted identifier or embed
        an SQL statement are rejected.
        """
        self.assertFalse(is_valid_postgresql_db_name('foo"bar'))
        self.assertFalse(is_valid_postgresql_db_name("foo'bar"))
        self.assertFalse(is_valid_postgresql_db_name('foo;bar'))
        self.assertFalse(is_valid_postgresql_db_name('foo\\bar'))
        self.assertFalse(is_valid_postgresql_db_name('foo\x00bar'))

    def test_rejects_whitespace(self):
        """Names containing any whitespace are rejected."""
        self.assertFalse(is_valid_postgresql_db_name('foo bar'))
        self.assertFalse(is_valid_postgresql_db_name('foo\tbar'))
        self.assertFalse(is_valid_postgresql_db_name('foo\nbar'))
        self.assertFalse(is_valid_postgresql_db_name('foo\rbar'))

    def test_rejects_overlong_names(self):
        """
        PostgreSQL silently truncates identifiers longer than 63 bytes,
        which would produce a database CodeChecker cannot reconnect to.
        """
        self.assertTrue(is_valid_postgresql_db_name('a' * 63))
        self.assertFalse(is_valid_postgresql_db_name('a' * 64))
        # 63 characters but more than 63 bytes due to multi-byte encoding.
        self.assertFalse(is_valid_postgresql_db_name('é' * 32))
