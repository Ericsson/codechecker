# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Unit tests for LDAP.
"""


import unittest

from mockldap import MockLdap

from codechecker_server.auth import cc_ldap


class CCLDAPTest(unittest.TestCase):

    top = ('o=test', {'o': ['test']})
    example = ('ou=example,o=test', {'ou': ['example']})
    other = ('ou=other,o=test', {'ou': ['other']})
    service_user = ('cn=service_user,ou=example,o=test',
                    {'cn': ['service_user'], 'userPassword': ['servicepw']})
    user2 = ('cn=user2,ou=other,o=test',
             {'cn': ['user2'], 'userPassword': ['user2pw']})

    # This is the content of our mock LDAP directory.
    # It takes the form {dn: {attr: [value, ...], ...}, ...}.
    directory = dict([top, example, other, service_user, user2])

    # service_user is used as a service user in the configuration.
    ldap_config = {"connection_url": "ldap://localhost/",
                   "username": "cn=service_user,ou=example,o=test",
                   "password": "servicepw",
                   "referrals": False,
                   "deref": "always",
                   "accountBase": "ou=other,o=test",
                   "accountScope": "subtree",
                   "accountPattern": "(cn=$USN$)",
                   "groupBase": "o=test",
                   "groupScope": "subtree",
                   "groupPattern": "",
                   "groupNameAttr": ""
                   }

    @classmethod
    def setup_class(cls):
        cls.mockldap = MockLdap(cls.directory)

    def setUp(self):
        # Patch ldap.initialize
        self.mockldap.start()
        self.ldapobj = self.mockldap['ldap://localhost/']

    def tearDown(self):
        # Stop patching ldap.initialize and reset state.
        self.mockldap.stop()
        del self.ldapobj

    def test_empty_config(self):
        """
        At least a connection_url is required in the ldap config.
        Without it no connection can be initialized.
        """
        with cc_ldap.LDAPConnection({}, None, None) as connection:
            self.assertIsNone(connection)

    def test_anonymous_bind(self):
        """
        Anonymous bind, without username and credentials.
        """
        with cc_ldap.LDAPConnection(self.ldap_config) as connection:
            self.assertIsNotNone(connection)

    def test_ldap_conn_context_bind_with_cred(self):
        """
        Bind to LDAP server with username and credentials.
        """
        ldap_config = {"connection_url": "ldap://localhost/"}

        with cc_ldap.LDAPConnection(ldap_config,
                                    'cn=service_user,ou=example,o=test',
                                    'servicepw') as connection:
            self.assertIsNotNone(connection)

    def test_ldap_conn_context_anonym_no_pass_bind(self):
        """
        Username and credentials are missing from the ldap config
        but username is provided at context initialization.
        """
        ldap_config = {"connection_url": "ldap://localhost/"}
        with cc_ldap.LDAPConnection(ldap_config,
                                    'cn=service_user,ou=example,o=test',
                                    '') as connection:
            self.assertIsNone(connection)

    def test_ldap_conn_context_anonym_empty_pass_bind(self):
        """
        Username and credentials are missing from the ldap config
        but username and credentials provided context initialization.
        """
        ldap_config = {"connection_url": "ldap://localhost/"}
        with cc_ldap.LDAPConnection(ldap_config,
                                    'cn=service_user,ou=example,o=test',
                                    'servicepw') as connection:
            self.assertIsNotNone(connection)

    def test_get_user_dn(self):
        """
        Search for the full user DN.
        """
        ldap_config = {"connection_url": "ldap://localhost/"}
        with cc_ldap.LDAPConnection(ldap_config,
                                    'cn=service_user,ou=example,o=test') \
                as connection:
            self.assertIsNotNone(connection)

            ret = cc_ldap.get_user_dn(connection,
                                      'ou=other,o=test',
                                      '(cn=user2)')

            self.assertEqual(ret, 'cn=user2,ou=other,o=test')

    def test_successful_auth(self):
        """
        Successful user authentication.
        """
        self.assertTrue(cc_ldap.auth_user(self.ldap_config,
                                          'user2',
                                          'user2pw'))

    def test_wrong_pwd(self):
        """
        Wrong password is provided, authentication should fail.
        """
        self.assertFalse(cc_ldap.auth_user(self.ldap_config,
                                           'user2',
                                           'wrong_password'))

    def test_missing_pwd(self):
        """
        Password is missing when auth_user function is called.
        """
        self.assertFalse(cc_ldap.auth_user(self.ldap_config, 'user2'))

    def test_empty_pwd(self):
        """
        Try to authenticate with empty password.
        """
        self.assertFalse(cc_ldap.auth_user(self.ldap_config, 'user2', ''))
