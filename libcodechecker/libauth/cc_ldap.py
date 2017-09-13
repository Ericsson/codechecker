# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""

LDAP authentication module for CodeChecker.
Authenticate user based on the session_config.json LDAP part.

In the configuration `null` means it is not configured.

"method_ldap": {
  "enabled" : true,
  "authorities": [
    {
      "connection_url" : null,
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

from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger("LDAP")


def log_ldap_error(ldap_error):
    """
    Log the LDAP error details in debug mode.
    """
    toprint = ''
    if ldap_error.message:
        if 'info' in ldap_error.message:
            toprint = toprint + ldap_error.message['info']
        if 'info' in ldap_error.message and 'desc' in ldap_error.message:
            toprint = toprint + "; "
        if 'desc' in ldap_error.message:
            toprint = toprint + ldap_error.message['desc']
    else:
        toprint = ldap_error.__repr__()
    LOG.debug(toprint)


@contextmanager
def ldap_error_handler():
    """
    Handle LDAP errors.
    """
    try:
        yield
    except ldap.INVALID_CREDENTIALS:
        LOG.error("Invalid credentials, please recheck "
                  "your authentication configuration.")

    except ldap.FILTER_ERROR:
        LOG.error("Filter error, please recheck your filter patterns.")

    except ldap.LDAPError as err:
        log_ldap_error(err)


def get_user_dn(con,
                account_base_dn,
                account_pattern,
                scope=ldap.SCOPE_SUBTREE):
    """
    Search for the user dn based on the account pattern.
    Return the full user dn None if search failed.
    """

    with ldap_error_handler():
        user_data = con.search_s(account_base_dn, scope, account_pattern)

        if user_data:
            # User found use the user DN from the first result.
            user_dn = user_data[0][0]
            LOG.debug("Found user: " + user_dn)
            return user_dn

    LOG.debug("Searching for user failed with pattern: " + account_pattern)
    LOG.debug("Account base DN:" + account_base_dn)
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
        group_result = connection.search_s(group_base,
                                           group_scope,
                                           member_query,
                                           ['memberOf'])

        # There is at least one match for one of the groups.
        return len(group_result) != 0


class LDAPConnection(object):
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

        ldap_server = ldap_config['connection_url']
        if ldap_server is None:
            LOG.error('Server address is missing from the configuration')
            return

        referals = ldap_config.get('referals', False)
        ldap.set_option(ldap.OPT_REFERRALS, 1 if referals else 0)

        deref = ldap_config.get('deref', ldap.DEREF_ALWAYS)
        if deref == 'never':
            deref = ldap.DEREF_NEVER
        else:
            deref = ldap.DEREF_ALWAYS

        ldap.set_option(ldap.OPT_DEREF, deref)

        ldap.protocol_version = ldap.VERSION3

        # Check cert if available but do not fail if not.
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)

        self.connection = ldap.initialize(ldap_server)

        LOG.debug('Binding to LDAP server with user: ' + who if who else '')

        with ldap_error_handler():
            if who is None or cred is None:
                # Try anonymous bind.
                res = self.connection.simple_bind_s()
                LOG.debug(res)
            else:
                # Bind with the given credentials
                LOG.debug(who)
                res = self.connection.simple_bind_s(who, cred)
                LOG.debug(res)

    def __enter__(self):
        return self.connection

    def __exit__(self, type, value, traceback):
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

    # Service user is not configured try to authenticate
    # with the given username and credentials.
    if not service_user:
        service_user = username
        service_cred = credentials
    with LDAPConnection(ldap_config, service_user, service_cred) as connection:

        user_dn = get_user_dn(connection,
                              account_base,
                              account_pattern,
                              account_scope)

        if user_dn is None:
            LOG.error('Please check your LDAP server '
                      'authentication credentials.')
            if service_user is None:
                LOG.error('Anonymous bind might not be enabled.')
            LOG.error('Configured username: ' + service_user)
            return False
    # bind with the users dn to check group membership
    with LDAPConnection(ldap_config, user_dn, credentials) as connection:
        return True
    LOG.info("User:" + username + " cannot be authenticated.")
    return False


def get_groups(ldap_config, username, credentials):

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

    LOG.debug("creating LDAP connection. service user" + service_user)
    with LDAPConnection(ldap_config, service_user, service_cred) as connection:
        user_dn = get_user_dn(connection,
                              account_base,
                              account_pattern,
                              account_scope)

        group_pattern = ldap_config.get('groupPattern', '')
        if user_dn and group_pattern == '':
            # User found and there is no group membership pattern to check.
            return []
        group_pattern = group_pattern.replace('$USERDN$', user_dn)

        LOG.debug('Checking for group membership.')

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

        # Attribute name must be ascii encoded
        group_name_attr = group_name_attr.encode('ascii',
                                                 'ignore')
        attr_list = [group_name_attr]

        LOG.debug("Performing LDAP search for group:" + group_pattern +
                  "Group Name Attr:" + group_name_attr)

        groups = []
        with ldap_error_handler():
            group_result = connection.search_s(group_base,
                                               group_scope,
                                               group_pattern,
                                               attr_list)
            if group_result:
                for g in group_result:
                    groups.append(g[1][group_name_attr][0])

        LOG.debug("groups:")
        LOG.debug(groups)
        return groups
    LOG.error("Cannot get ldap groups for user:"+username)
    return []
