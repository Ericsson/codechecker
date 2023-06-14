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
import subprocess
import unittest

from codechecker_api_shared.ttypes import Permission, RequestFailed

from libtest import codechecker, env

from . import setup_class_common, teardown_class_common


class PermissionManagement(unittest.TestCase):

    def setup_class(self):
        setup_class_common()

    def teardown_class(self):
        teardown_class_common()

    def setup_method(self, method):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self._test_workspace = os.environ['TEST_WORKSPACE']

        # Display test name to log.
        test_class = self.__class__.__name__
        print(f"Running {test_class} tests in {self._test_workspace}")

        # Get the test configuration from the prepared int the test workspace.
        test_config = env.import_test_cfg(self._test_workspace)
        self.codechecker_cfg = test_config['codechecker_cfg']

        # Log in and create credential file (if it is not exists).
        self.superuser_name = "root"
        self.superuser_passwd = "root"

        codechecker.login(test_config['codechecker_cfg'],
                          self._test_workspace, self.superuser_name,
                          self.superuser_passwd)

        self.temp_auth_client = env.setup_auth_client(
            self._test_workspace, session_token='_PROHIBIT')

        # A non-authenticated session should return an empty user.
        user_name = self.temp_auth_client.getLoggedInUser()
        self.assertEqual(user_name, "")

        self.root_client = self.__get_auth_client(
            self.superuser_name, self.superuser_passwd)

    def __get_auth_client(self, username, password):
        """ """
        # Create a SUPERUSER login.
        session_token = self.temp_auth_client.performLogin(
            "Username:Password", f"{username}:{password}")
        self.assertIsNotNone(
            session_token, "Valid credentials didn't give us a token!")

        # Connect as root to the server.
        auth_client = env.setup_auth_client(
            self._test_workspace, session_token=session_token)
        user_name = auth_client.getLoggedInUser()
        self.assertEqual(user_name, username)

        return auth_client

    def test_get_access_control_with_permission_viewer(self):
        """
        Test getting access control information from the server with a
        user who has PERMISSION_VIEW rights.
        """
        # Add permissions.
        ret = self.root_client.addPermission(
            Permission.PERMISSION_VIEW, "permission_view_user", False, None)
        self.assertTrue(ret)

        ret = self.root_client.addPermission(
            Permission.PERMISSION_VIEW, "permission_view_group", True, None)
        self.assertTrue(ret)

        client = self.__get_auth_client("permission_view_user", "pvu")
        access_control = client.getAccessControl()

        global_permissions = access_control.globalPermissions

        # Only default superuser is returned.
        self.assertTrue(len(global_permissions.user), 2)

        permissions = global_permissions.user["permission_view_user"]
        self.assertTrue(len(permissions), 1)
        self.assertIn("PERMISSION_VIEW", permissions)

        self.assertDictContainsSubset(
            {'permission_view_group': ['PERMISSION_VIEW']},
            global_permissions.group)

        product_permissions = access_control.productPermissions
        self.assertTrue(product_permissions)

        auth_product_permissions = product_permissions["authentication"]
        self.assertDictContainsSubset(
            {'cc': ['PRODUCT_STORE'],
             'john': ['PRODUCT_STORE'],
             'admin': ['PRODUCT_ADMIN']},
            auth_product_permissions.user)

        # Previously, the test files in this directory interfered at one
        # another, and the group permission dict wasn't empty. Check git blame.
        self.assertEqual({}, auth_product_permissions.group)

        # Remove previously added extra permissions.
        ret = self.root_client.removePermission(
            Permission.PERMISSION_VIEW, "permission_view_user", False, None)
        self.assertTrue(ret)

        ret = self.root_client.removePermission(
            Permission.PERMISSION_VIEW, "permission_view_group", True, None)
        self.assertTrue(ret)

    def test_get_access_control_with_superuser(self):
        """
        Test getting access control information from the server with a
        superuser.
        """
        client = self.__get_auth_client(
            self.superuser_name, self.superuser_passwd)

        access_control = client.getAccessControl()

        global_permissions = access_control.globalPermissions
        self.assertEqual(len(global_permissions.user), 1)

        # Only default superuser is returned.
        permissions = global_permissions.user[
            next(iter(global_permissions.user))]
        self.assertEqual(permissions, ["SUPERUSER"])

    def test_get_access_control_with_no_permission(self):
        """
        Test getting access control information from the server with a
        user who has no rights.
        """
        client = self.__get_auth_client("john", "doe")

        with self.assertRaises(RequestFailed):
            client.getAccessControl()

    def test_get_access_control_from_cli(self):
        """ Test getting access control information by using CLI. """
        cmd_env = os.environ.copy()
        cmd_env["CC_PASS_FILE"] = os.path.join(
            self._test_workspace, ".codechecker.passwords.json")
        cmd_env["CC_SESSION_FILE"] = os.path.join(
            self._test_workspace, ".codechecker.session.json")

        cmd = [env.codechecker_cmd(), 'cmd', 'permissions',
               '--url', env.parts_to_url(self.codechecker_cfg)]

        out = subprocess.check_output(
            cmd, env=cmd_env, encoding="utf-8", errors="ignore")

        access_control = json.loads(out)

        # Previously, the test files in this directory interfered at one
        # another, and the group permission dict wasn't empty. Check git blame.
        self.assertDictEqual({
            "version": 1,
            "global_permissions": {
                "user_permissions": {
                    "root": ["SUPERUSER"]},
                "group_permissions": {}
            },
            "product_permissions": {
                "authentication": {
                    "user_permissions": {
                        "cc": ["PRODUCT_STORE"],
                        "john": ["PRODUCT_STORE"],
                        "admin": ["PRODUCT_ADMIN"]},
                    "group_permissions": {}}}},
            access_control)
