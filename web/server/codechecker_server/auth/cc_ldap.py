# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""

LDAP authentication module for CodeChecker.
Authenticate user based on the server_config.json LDAP part.

In the configuration `null` means it is not configured.

"method_ldap": {
  "enabled" : true,
  "authorities": [
    {
      "connection_url" : null,
      "tls_require_cert" : null,
      "username" : null,
      "password" : null,
      "referrals" : false,
      "deref" : "always",
      "accountBase" : null,
      "accountScope" : "subtree",
      "accountPattern" : null,
      "groupBase" : null,
      "groupScope" : "subtree",
      "groupPattern" : null,
      "groupNameAttr" : null
    }
  ]
},


##### Configuration options:

`connection_url`
URL of the LDAP server which will be queried for user information and group
membership.

`username`
Optional username for LDAP bind, if not set bind with the
login credentials will be attempted.

`password`
Optional password for configured username.

`referrals`
Microsoft Active Directory by returns referrals (search continuations). LDAPv3
does not specify which credentials should be used by the clients when chasing
these referrals and will be tried as an anonymous access by the libldap library
which might fail. Will be disabled by default.

`deref`
Configure how the alias dereferencing is done in libldap
(valid values: always, never).

`accountBase`
Root tree containing all the user accounts.

`accountScope`
Scope of the search performed. Accepted values are: base, one, subtree.

`accountPattern`
The special `$USN$` token in the query is replaced to the *username* at login.
Query pattern used to search for a user account. Must be a valid LDAP query
expression.
Example configuration: *(&(objectClass=person)(sAMAccountName=$USN$))*

`groupBase`
Root tree containing all the groups.

`groupPattern`

Group query pattern used LDAP query expression to find the group objects
a user is a member of. It must contain a `$USERDN$` pattern.
`$USERDN$` will be automatically replaced by the queried user account DN.

`groupNameAttr`

The attribute of the group object which contains the name of the group.

`groupScope`
Scope of the search performed. (Valid values are: base, one, subtree)


"""


from contextlib import contextmanager

import ldap
from ldap.dn import escape_dn_chars

from codechecker_common.logger import get_logger

LOG = get_logger('server')


def bytes_to_str(data):
    """ Converts the given data to text.

    The LDAP protocol states that some fields be encoded in UTF-8. Attribute
    values, on the other hand, MAY contain any type of data, including text.
    Encoding/decoding to other formats – text, images, etc. – is left to the
    caller. See:
    https://www.python-ldap.org/en/python-ldap-3.2.0/bytes_mode.html
    """
    if isinstance(data, bytes):
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError as err:
            LOG.error("Failed to convert byte (%s) to text: %s", data, err)
            return ''

    return data


@contextmanager
def ldap_error_handler():
    """
    Handle LDAP errors.
    """
    try:
        yield
    except ldap.INVALID_CREDENTIALS:
        LOG.warning("Invalid credentials, please recheck "
                    "your authentication configuration.")

    except ldap.FILTER_ERROR as ex:
        LOG.error("Filter error: %s", str(ex))

    except ldap.SERVER_DOWN:
        LOG.error("Can't connect to LDAP server,"
                  " or LDAPS certificate verification failed")

    except ldap.LDAPError as err:
        LOG.error("Exception ldap.%s (%s)",
                  type(err).__name__, str(err))


def get_user_dn(con,
                account_base_dn,
                account_pattern,
                scope=ldap.SCOPE_SUBTREE,
                user_dn_postfix_preference=None):
    """
    Search for the user dn based on the account pattern.
    Return the full user dn None if search failed.

    Parameters:
      user_dn_postfix_preference: User DN postfix preference value can
      be used to select out one prefered
      user DN if multiple DN entries are found by the LDAP search.
      The configured value will be matched and the first matching will be used.
      If only one DN was found this postfix matching will not be used.
      If not set and multiple values are found the first value
      in the search result list will be used.
    """

    with ldap_error_handler():
        # Attribute values MAY contain any type of data. Before you use a
        # value, call 'bytes_to_str' helper function to convert it to text.
        user_data = con.search_s(account_base_dn, scope, account_pattern)
        user_dns = []
        if user_data:
            # User found use the user DN from the first result.
            for user_info in user_data:
                user_dns.append(bytes_to_str(user_info[0]))
            LOG.debug("Found user dns: %s", ', '.join(user_dns))

            if len(user_dns) > 1 and user_dn_postfix_preference:
                for user_dn in user_dns:
                    if user_dn.endswith(user_dn_postfix_preference):
                        LOG.debug("Selected user dn: %s", user_dn)
                        return user_dn
            elif len(user_dns) > 0:
                LOG.debug("Selected user dn: %s", user_dns[0])
                return user_dns[0]

    LOG.debug("Searching for user failed with pattern: %s", account_pattern)
    LOG.debug("Account base DN: %s", account_base_dn)
    return None


def check_group_membership(connection,
                           group_base,
                           member_query,
                           group_scope):
    """
    Check if a user is a member of an LDAP group using the memberOf
    attribute.
    """

    LOG.debug(member_query)

    with ldap_error_handler():
        # Attribute values MAY contain any type of data. Before you use a
        # value, call 'bytes_to_str' helper function to convert it to text.
        group_result = connection.search_s(group_base,
                                           group_scope,
                                           member_query,
                                           ['memberOf'])

        # There is at least one match for one of the groups.
        return len(group_result) != 0

    return False


class LDAPConnection:
    """
    A context manager class to initialize an LDAP connection
    and bind to the LDAP server.
    """

    def __init__(self, ldap_config, who=None, cred=None):
        """
        Initialize an ldap connection object and bind to the configured
        LDAP server.
        None if initialization failed.
        """

        ldap_server = ldap_config.get('connection_url')
        if ldap_server is None:
            LOG.error('Server address is missing from the configuration')
            self.connection = None
            return

        referrals = ldap_config.get('referrals', False)
        ldap.set_option(ldap.OPT_REFERRALS, 1 if referrals else 0)

        deref = ldap_config.get('deref', ldap.DEREF_ALWAYS)
        if deref == 'never':
            deref = ldap.DEREF_NEVER
        else:
            deref = ldap.DEREF_ALWAYS

        ldap.set_option(ldap.OPT_DEREF, deref)

        ldap.protocol_version = ldap.VERSION3

        # Verify certificate in LDAPS connections
        tls_require_cert = ldap_config.get('tls_require_cert', '')
        if tls_require_cert.lower() == 'never':
            LOG.debug("Insecure LDAPS connection because of "
                      "tls_require_cert=='never'")
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        self.connection = ldap.initialize(ldap_server, bytes_mode=False)

        LOG.debug('Binding to LDAP server with user: %s', who if who else '')

        res = None
        with ldap_error_handler():
            if who is None or cred is None:
                LOG.debug("Anonymous bind with no credentials.")
                res = self.connection.simple_bind_s()
                LOG.debug(res)
            else:
                LOG.debug("Binding with credential: %s", who)
                res = self.connection.simple_bind_s(who, cred)
                whoami = self.connection.whoami_s()
                LOG.debug(res)
                LOG.debug(whoami)

                # mail.python.org/pipermail/python-ldap/2012q4/003180.html
                if whoami is None:
                    # If LDAP server allows anonymous binds, simple bind
                    # does not throw an exception when the password is
                    # empty and does the binding as anonymous.
                    # This is an expected behaviour as per LDAP RFC.

                    # However, if the bind is successful but no
                    # authentication has been done, it is still to be
                    # considered an error from the user's perspective.
                    LOG.debug("Anonymous bind succeeded but no valid "
                              "password was given.")
                    raise ldap.INVALID_CREDENTIALS()

        if not res:
            LOG.debug("Server bind failed.")
            if self.connection is not None:
                self.connection.unbind()
            self.connection = None

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, value, traceback):
        if self.connection is not None:
            self.connection.unbind()


def get_ldap_query_scope(scope_form_config):
    """
    Return an ldap scope base on the configured value.
    The defaul scope is the subtree.
    """
    # the default scope is the subtree
    if scope_form_config == 'base':
        return ldap.LDAP_SCOPE_BASE
    elif scope_form_config == 'one':
        return ldap.LDAP_SCOPE_ONELEVEL
    else:
        return ldap.SCOPE_SUBTREE


def auth_user(ldap_config, username=None, credentials=None):
    """
    Authenticate a user.
    """
    if not username or not credentials:
        LOG.warning('No username or credential is provided for'
                    ' authentication.')
        return False

    account_base = ldap_config.get('accountBase')
    if account_base is None:
        LOG.warning('Account base needs to be configured to query users')
        return False

    account_pattern = ldap_config.get('accountPattern')
    if account_pattern is None:
        LOG.warning('No account pattern is defined to search for users.')
        LOG.warning('Please configure one.')
        return False

    username = escape_dn_chars(username)
    account_pattern = account_pattern.replace('$USN$', username)

    account_scope = ldap_config.get('accountScope', '')
    account_scope = get_ldap_query_scope(account_scope)

    service_user = ldap_config.get('username')
    service_cred = ldap_config.get('password')

    # Service user is not configured try to authenticate
    # with the given username and credentials.
    if not service_user:
        service_user = username
        service_cred = credentials

    LOG.debug("Creating SERVICE connection...")

    user_dn_postfix_preference = ldap_config.get('user_dn_postfix_preference')

    with LDAPConnection(ldap_config, service_user, service_cred) as connection:
        if connection is None:
            LOG.error('Please check your LDAP server '
                      'authentication credentials.')
            LOG.error('Configured username: %s', service_user)
            return False

        user_dn = get_user_dn(connection,
                              account_base,
                              account_pattern,
                              account_scope,
                              user_dn_postfix_preference)

        if user_dn is None:
            LOG.warning("DN lookup failed for user name: '%s'!", username)
            if service_user is None:
                LOG.warning('Anonymous bind might not be enabled.')
            return False

    # Bind with the user's DN to check the password given by the user.
    # If bind is successful the user has given the right password.
    LOG.debug("Creating USER connection...")
    with LDAPConnection(ldap_config, user_dn, credentials) as connection:
        if not connection:
            LOG.info("User: %s cannot be authenticated.", username)

        return connection is not None


def get_groups(ldap_config, username, credentials):
    """
    Get the LDAP groups for a given user.
    """

    account_base = ldap_config.get('accountBase')
    if account_base is None:
        LOG.error('Account base needs to be configured to query users')
        return False

    account_pattern = ldap_config.get('accountPattern')
    if account_pattern is None:
        LOG.error('No account pattern is defined to search for users.')
        LOG.error('Please configure one.')
        return False

    account_pattern = account_pattern.replace('$USN$', username)

    account_scope = ldap_config.get('accountScope', '')
    account_scope = get_ldap_query_scope(account_scope)

    service_user = ldap_config.get('username')
    service_cred = ldap_config.get('password')
    if not service_user:
        service_user = username
        service_cred = credentials

    user_dn_postfix_preference = ldap_config.get('user_dn_postfix_preference')

    LOG.debug("creating LDAP connection. service user %s", service_user)
    with LDAPConnection(ldap_config, service_user, service_cred) as connection:
        if connection is None:
            LOG.error('Please check your LDAP server '
                      'authentication credentials.')
            return False

        user_dn = get_user_dn(connection,
                              account_base,
                              account_pattern,
                              account_scope,
                              user_dn_postfix_preference)

        group_pattern = ldap_config.get('groupPattern')
        if user_dn and not group_pattern:
            LOG.debug("User '%s' found but there is no group_pattern"
                      " to check LDAP for group membership.",
                      user_dn)
            return []
        group_pattern = group_pattern.replace('$USERDN$', user_dn)

        LOG.debug('Checking for group membership %s', user_dn)

        group_scope = ldap_config.get('groupScope', '')
        group_scope = get_ldap_query_scope(group_scope)

        group_base = ldap_config.get('groupBase')
        if group_base is None:
            LOG.error('Group base needs to be configured to'
                      'query ldap groups.')
            return []

        group_name_attr = ldap_config.get('groupNameAttr')
        if group_name_attr is None:
            LOG.error('groupNameAttr needs to be configured to'
                      'query ldap groups.'
                      'Its value must be the name'
                      'attribute of the group.')
            return []

        # Remove non ascii characters.
        group_name_attr = \
            group_name_attr.encode('ascii', 'ignore').decode('utf-8')
        attr_list = [group_name_attr]

        LOG.debug("Performing LDAP search for group: %s Group Name Attr: %s",
                  group_pattern, group_name_attr)

        groups = []
        with ldap_error_handler():
            # Attribute values MAY contain any type of data. Before you use a
            # value, call 'bytes_to_str' helper function to convert it to text.
            group_result = connection.search_s(group_base,
                                               group_scope,
                                               group_pattern,
                                               attr_list)
            if group_result:
                for g in group_result:
                    groups.append(bytes_to_str(g[1][group_name_attr][0]))

        LOG.debug("groups:")
        LOG.debug(groups)
        return groups
