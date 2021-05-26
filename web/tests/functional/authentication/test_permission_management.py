#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Tests for permission management.
"""

import json
import os
import unittest

from codechecker_api_shared.ttypes import Permission

from libtest import codechecker, env


class PermissionManagement(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self._test_workspace = os.environ['TEST_WORKSPACE']

        # Display test name to log.
        test_class = self.__class__.__name__
        print(f"Running {test_class} tests in {self._test_workspace}")

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
            "Username:Password", f"{superuser_name}:{superuser_passwd}")
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

        self._extra_params = json.dumps({'productID': self._product_id})

    def __get_real_group_name(self, group_name_guess):
        """
        Helper to determine the real group name stored in the database.
        """

        group_name_lower = group_name_guess.lower()
        product_permissions = self._root_auth_client.getPermissions('PRODUCT')
        for permission in product_permissions:
            authorized_names = self._root_auth_client.getAuthorisedNames(
                permission, self._extra_params)
            for group in authorized_names.groups:
                if group.lower() == group_name_lower:
                    return group

    def test_product_permissions(self):
        """
        Tests if server side supported product permissions changed or not.
        """

        product_permissions = self._root_auth_client.getPermissions('PRODUCT')
        expected_permissions = [Permission.PRODUCT_ADMIN,
                                Permission.PRODUCT_ACCESS,
                                Permission.PRODUCT_STORE,
                                Permission.PRODUCT_VIEW]
        self.assertSetEqual(
            set(expected_permissions), set(product_permissions),
            "PRODUCT permission set in the database is different.")

    def test_system_permissions(self):
        """
        Tests if server side supported system permissions changed or not.
        """
        sys_permissions = self._root_auth_client.getPermissions('SYSTEM')
        expected_permissions = [Permission.SUPERUSER]
        self.assertSetEqual(
            set(expected_permissions), set(sys_permissions),
            "SYSTEM permission set in the database is different.")

    def test_user_product_permissions(self):
        """
        Tests user's product permission handling in the server.

        User names should be handled by case insensitive way, because the
        underlying LDAP authentication system also case insensitive.
        """
        normal_test_user_name = "john"
        as_user = False
        expected_permission = Permission.PRODUCT_STORE

        # Check test user if he is in the authorization database with
        # PRODUCT_STORE right.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        self.assertIn(normal_test_user_name, authorized_names.users,
                      "Test database mismatch.")

        # Check test user has not got PRODUCT_ACCESS permission for test
        # product.
        expected_permission = Permission.PRODUCT_ACCESS
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        self.assertNotIn(normal_test_user_name, authorized_names.users,
                         "Test database mismatch.")

        # Add John to the test product with PRODUCT_ACCESS permission.
        # But his name is in uppercase form.
        result = self._root_auth_client.addPermission(
            expected_permission, normal_test_user_name.upper(), as_user,
            self._extra_params)
        self.assertTrue(result)

        # Read back John's permission with his "original" name.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        self.assertIn(normal_test_user_name, authorized_names.users,
                      "Could not give permission for user.")

        # Remove permission from John with uppercase name.
        result = self._root_auth_client.removePermission(
            expected_permission, normal_test_user_name.upper(), as_user,
            self._extra_params)
        self.assertTrue(result)

        # Check that John really loose his PRODUCT_ACCESS permission.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        for user in authorized_names.users:
            self.assertNotEqual(normal_test_user_name.lower(), user.lower())

    def test_group_product_permissions(self):
        """
        Tests product permissions of group handling in the server.

        User names should be handled by case insensitive way, because the
        underlying LDAP authentication system also case insensitive.
        """
        admin_test_group_name = "admin_GROUP"
        as_group = True
        expected_permission = Permission.PRODUCT_STORE
        # Check test group if it is in the authorization database with
        # PRODUCT_STORE right.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        for group in authorized_names.groups:
            self.assertNotEqual(admin_test_group_name.lower(), group.lower(),
                                "Test database mismatch.")

        # Check test user has not got PRODUCT_ACCESS permission for test
        # product.
        expected_permission = Permission.PRODUCT_ACCESS
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        for group in authorized_names.groups:
            self.assertNotEqual(admin_test_group_name.lower(), group.lower(),
                                "Test database mismatch.")

        # Try to find test group name in the permissions table.
        stored_group_name = self.__get_real_group_name(admin_test_group_name)
        if not stored_group_name:
            stored_group_name = admin_test_group_name

        # Add admin_GROUP to the test product with PRODUCT_STORE permission.
        result = self._root_auth_client.addPermission(
            expected_permission, stored_group_name, as_group,
            self._extra_params)
        self.assertTrue(result)

        # Add admin_GROUP to the test product with PRODUCT_ACCESS permission.
        # But its name is in uppercase form.
        result = self._root_auth_client.addPermission(
            expected_permission, stored_group_name.upper(), as_group,
            self._extra_params)
        self.assertTrue(result)

        # Read back permission of admin_GROUP with its "original" name.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        self.assertIn(stored_group_name, authorized_names.groups,
                      "Could not give permission for group.")

        # Remove PRODUCT_ACCESS permission from admin_GROUP.
        # But with lowercase name.
        result = self._root_auth_client.removePermission(
            expected_permission, stored_group_name.lower(), as_group,
            self._extra_params)
        self.assertTrue(result)

        # Check that admin_GROUP really loose its PRODUCT_ACCESS permission.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        for group in authorized_names.groups:
            self.assertNotEqual(stored_group_name.lower(), group.lower())

        # Remove PRODUCT_STORE permission from admin_GROUP.
        # But with uppercase name.
        expected_permission = Permission.PRODUCT_STORE
        result = self._root_auth_client.removePermission(
            expected_permission, stored_group_name.upper(), as_group,
            self._extra_params)
        self.assertTrue(result)

        # Check that admin_GROUP really loose its PRODUCT_STORE permission too.
        authorized_names = self._root_auth_client.getAuthorisedNames(
            expected_permission, self._extra_params)
        for group in authorized_names.groups:
            self.assertNotEqual(stored_group_name.lower(), group.lower())
