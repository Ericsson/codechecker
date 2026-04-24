# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for the request_routing module. """


import unittest

from codechecker_server.routing import split_client_GET_request
from codechecker_server.routing import split_client_POST_request
from codechecker_server.routing import is_valid_postgresql_db_name


def get(path, host="http://localhost:8001/"):
    return split_client_GET_request(host + path.lstrip('/'))


def post(path):
    return split_client_POST_request("http://localhost:8001/" +
                                     path.lstrip('/'))


class RequestRoutingTest(unittest.TestCase):
    """
    Testing the router that understands client request queries.
    """

    def test_get(self):
        """
        Test if the server properly splits query addresses for GET.
        """

        self.assertEqual(get(''), (None, ''))
        self.assertEqual(get('/', '//'), (None, ''))
        self.assertEqual(get('index.html'), (None, 'index.html'))
        self.assertEqual(get('/images/logo.png'),
                         (None, 'images/logo.png'))

        self.assertEqual(get('Default'), ('Default', ''))
        self.assertEqual(get('Default/index.html'), ('Default', 'index.html'))

    def test_post(self):
        """
        Test if the server properly splits query addresses for POST.
        """

        # The splitter returns (None, None, None) as these are invalid paths.
        # It is the server code's responsibility to give a 404 Not Found.
        self.assertEqual(post(''), (None, None, None))
        self.assertEqual(post('CodeCheckerService'), (None, None, None))
        self.assertEqual(post('v6.0'), (None, None, None))
        self.assertEqual(post('/v6.0/product/Authentication/Service'),
                         (None, None, None))

        self.assertEqual(post('/v6.0/Authentication'),
                         (None, '6.0', 'Authentication'))

        self.assertEqual(post('/DummyProduct/v6.0/FoobarService'),
                         ('DummyProduct', '6.0', 'FoobarService'))


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
