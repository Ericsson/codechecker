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
from unittest.mock import patch

from codechecker_common.configuration_access import \
    Configuration, OptionDirectory, Schema

from codechecker_server.auth import cc_ldap
from codechecker_server.server_configuration import \
    register_configuration_options


class MockLdap:
    def __init__(self, directory) -> None:
        self.directory = directory

    def simple_bind_s(
        self,
        who=None,
        cred=None,
        _serverctrls=None,
        _clientctrls=None
    ):
        success = False

        if not who and not cred:
            success = True
        elif cred in self.directory[who.lower()]['userPassword']:
            success = True

        return 42 if success else None

    def unbind(self):
        pass

    def whoami_s(self):
        return "Joe"

    def search_s(
        self,
        base,
        _scope,
        filterstr='(objectClass=*)',
        _attrlist=None,
        _attrsonly=0
    ):
        if base == 'ou=other,o=test' and filterstr == '(cn=user2)':
            return [(
                'cn=user2,ou=other,o=test',
                {'cn': ['user2'], 'userPassword': ['user2pw']})]
        return []


SERVER_CFG_SCHEMA = register_configuration_options(Schema())


def _make_ldap_config(authority_configuration: dict) -> OptionDirectory:
    full_config_stub = {
        "authentication": {
            "method_ldap": {
                "authorities": [authority_configuration]
            }
        }
    }
    cfg = Configuration.from_memory(SERVER_CFG_SCHEMA, full_config_stub)
    return cfg.authentication.method_ldap.authorities[0]


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

    _ldap_config = {
        "connection_url": "ldap://localhost/",
        # service_user is used as a service user in the configuration.
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
    ldap_config = _make_ldap_config(_ldap_config)

    def setUp(self):
        self.ldap_patcher = patch('ldap.initialize')
        self.mock_ldap = self.ldap_patcher.start()
        self.mock_ldap.return_value = MockLdap(self.directory)

    def test_empty_config(self):
        """
        At least a connection_url is required in the ldap config.
        Without it no connection can be initialized.
        """
        ldap_config = _make_ldap_config({})
        with cc_ldap.LDAPConnection(ldap_config, None, None) as connection:
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
        ldap_config = _make_ldap_config(ldap_config)

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
        ldap_config = _make_ldap_config(ldap_config)

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
        ldap_config = _make_ldap_config(ldap_config)

        with cc_ldap.LDAPConnection(ldap_config,
                                    'cn=service_user,ou=example,o=test',
                                    'servicepw') as connection:
            self.assertIsNotNone(connection)

    def test_get_user_dn(self):
        """
        Search for the full user DN.
        """
        ldap_config = {"connection_url": "ldap://localhost/"}
        ldap_config = _make_ldap_config(ldap_config)

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
