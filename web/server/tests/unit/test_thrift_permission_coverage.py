# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Verify that every Thrift API method on the report server has a
detectable permission check.

This guards against a class of security bug: a Thrift method that is
exposed to the JavaScript client but lacks a permission check, allowing
an unprivileged user to invoke functionality reserved for product
admins or other higher-privileged roles.

The same check is also run at server startup; this test exists to fail
PR CI early, before such a regression can be merged.
"""
import unittest

from codechecker_server.api.permission_coverage import (
    assert_all_thrift_methods_protected,
)


class ThriftPermissionCoverageTest(unittest.TestCase):
    def test_all_thrift_methods_protected(self):
        """Every Thrift method on ThriftRequestHandler is protected by
        either an @requires_view decorator, a self.__require_*() call
        in its first few statements, or an audited entry in
        _DELEGATED_PROTECTION."""
        # Raises RuntimeError listing offenders if any method is
        # unprotected; the unittest framework converts the raise into
        # a test failure with that message visible.
        assert_all_thrift_methods_protected()
