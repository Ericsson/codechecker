#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Tests for authentication management.
"""

import json
import os
import unittest

from codechecker_api_shared.ttypes import Permission

from libtest import codechecker
from libtest import env


class PermissionManagement(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self._test_workspace = os.environ['TEST_WORKSPACE']

        # Display test name to log.
        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        test_config = env.import_test_cfg(self._test_workspace)

        # Log in and create credential file (if it is not exists).
        superuser_name = "root"
        superuser_passwd = "root"

        codechecker.login(test_config['codechecker_cfg'],
                          self._test_workspace, superuser_name,
                          superuser_passwd)

        temp_auth_client = env.setup_auth_client(self._test_workspace,
                                                 session_token='_PROHIBIT')

        # A non-authenticated session should return an empty user.
        user_name = temp_auth_client.getLoggedInUser()
        self.assertEqual(user_name, "")

        # Create a SUPERUSER login.
        self._session_token = temp_auth_client.performLogin(
            "Username:Password", superuser_name + ":" + superuser_passwd)
        self.assertIsNotNone(self._session_token,
                             "Valid credentials didn't give us a token!")

        # Connect as root to the server.
        self._root_auth_client = env.setup_auth_client(
            self._test_workspace, session_token=self._session_token)
        user_name = self._root_auth_client.getLoggedInUser()
        self.assertEqual(user_name, superuser_name)

        # Query data of current product
        self._product_name = test_config['codechecker_cfg']['viewer_product']
        self._product_client = env.setup_product_client(
            self._test_workspace, product=self._product_name)
        self.assertIsNotNone(self._product_client)
        self._current_product = self._product_client.getCurrentProduct()
        self.assertIsNotNone(self._current_product)
        self._product_id = self._current_product.id
        self.assertIsNotNone(self._product_id)

        extra_params = {'productID': self._product_id}
        self._extra_params_as_json = json.dumps(extra_params)

    def test_product_permissions(self):
        product_permissions = self._root_auth_client.getPermissions('PRODUCT')
        product_permission_set = set(product_permissions)
        expected_permission_set = set(
            [Permission.PRODUCT_ADMIN, Permission.PRODUCT_ACCESS,
             Permission.PRODUCT_STORE])
        self.assertSetEqual(
            expected_permission_set, product_permission_set,
            "PRODUCT permission set in the database is different.")

    def test_system_permissions(self):
        sys_permissions = self._root_auth_client.getPermissions('SYSTEM')
        sys_permission_set = set(sys_permissions)
        expected_permission_set = set(
            [Permission.SUPERUSER])
        self.assertSetEqual(
            expected_permission_set, sys_permission_set,
            "SYSTEM permission set in the database is different.")

    def test_user_product_permissions(self):
        normal_test_user_name = "john"
        as_user = False
        expected_permission = Permission.PRODUCT_STORE

        # Check test user if he is in the authorization database with
        # PRODUCT_STORE right.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params_as_json)
        self.assertIn(normal_test_user_name, authorized_names.users,
                      "Test database mismatch.")

        # Check test user has not got PRODUCT_ACCESS permission for test
        # product.
        expected_permission = Permission.PRODUCT_ACCESS
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params_as_json)
        self.assertNotIn(normal_test_user_name, authorized_names.users,
                         "Test database mismatch.")

        # Add John to the test product with PRODUCT_ACCESS permission.
        # But his name is in uppercase form.
        result = self._root_auth_client.addPermission(
            expected_permission, normal_test_user_name.upper(), as_user,
            self._extra_params_as_json)
        self.assertTrue(result)

        # Read back John's permission with his "original" name.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params_as_json)
        self.assertIn(normal_test_user_name, authorized_names.users,
                      "Could not give permission for user.")

        # Remove permission from John with uppercase name.
        result = self._root_auth_client.removePermission(
            expected_permission, normal_test_user_name.upper(), as_user,
            self._extra_params_as_json)
        self.assertTrue(result)

        # Check that John really loose his PRODUCT_ACCESS permission.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params_as_json)
        for user in authorized_names.users:
            self.assertNotEqual(normal_test_user_name.lower(), user.lower())

    # TODO: Create tests for group permissions too.
