CodeChecker authentication subsytem
===================================

# Please be advised, that currently, login credentials travel on an unencrypted channel!

CodeChecker also supports only allowing a privileged set of users to access the results stored on a server.

> **NOTICE!** Some authentication subsystems require additional packages to be installed before they can be used. See below.

## Serverside configuration

The server's configuration is stored in the server's *workspace* folder, in `session_config.json`.
This file is created, at the first start of the server, using the package's installed `config/session_config.json` as a template.

The `authentication` section of the config file controls how authentication is handled.

 * `enabled`

    Setting this to `false` disables privileged access
 * `realm_name`

    The name to show for web-browser viewers' pop-up login window via *HTTP Authenticate*
 * `realm_error`

    The error message shown in the browser when the user fails to authenticate
 * `logins_until_cleanup`

    After this many login attempts made towards the server, it will perform an automatic cleanup of old, expired sessions.
 * `soft_expire`

    (in seconds) When a user is authenticated, a session is created for them and this session identifies the user's access.
    This configuration variable sets how long the session considered "valid" before the user is needed
    to reauthenticate again &mdash; if this time expires, the session will be *hibernated*: the next access will be denied,
    but if the user presents a valid login, they will get their session reused.
 * `session_lifetime`

    (in seconds) The lifetime of the session sets that after this many seconds since last session access the session is permanently invalidated.

Every authentication method is its own JSON object in this section. Every authentication method has its
own `enabled` key which dictates whether it is used at live authentication or not.

Users are authenticated if **any** authentication method successfully authenticates them.
Authentications are attempted in the order they are described here: *dicitonary* takes precedence,
*pam* is a secondary and *ldap* is a tertiary backend, if enabled.

### <i>Dictionary</i> authentication

The `authentication.method_dictionary` contains a plaintext `username:password` credentials for authentication.
If the user's login matches any of the credentials listed, the user will be authenticated.

~~~{.json}
"method_dictionary": {
  "enabled" : true,
  "auths" : [
      "global:admin",
      "test:test"
  ]
}
~~~

### External authentication methods

External authentication methods connect to a privilege manager to authenticate users against.

Using external authentication methods - such as *PAM* or *LDAP* - require additional packages and libraries to be installed on the system.

~~~{.sh}
# get additional system libraries
sudo apt-get install libldap2-dev libsasl2-dev libssl-dev

# the python virtual environment must be sourced!
source ~/checker_env/bin/activate

# install required python modules
pip install -r .ci/auth_requirements
~~~

#### <i>PAM</i> authentication

To access the server via PAM authentication, the user must provide valid username and password which is accepted by PAM.

~~~{.json}
"method_pam": {
  "enabled" : true
}
~~~

The module can be configured to allow specific users or users belonging to specific groups only.
In the example below, `root` and `myname` can access the server, and **everyone** who belongs to the `adm` or `cc-users` group can access the server.

~~~{.json}
"method_pam": {
  "enabled" : true,
  "users": [
    "root", "myname"
  ],
  "groups": [
    "adm", "cc-users"
  ]
}
~~~

#### <i>LDAP</i> authentication

CodeChecker also supports *LDAP*-based authentication. The `authentication.method_ldap` section contains the configuration for LDAP authentication:
the server can be configured to connect to as much LDAP-servers as the administrator wants. Each LDAP server is identified by a `connection_url` and a list of `queries`
to attempt to log in the username given.

Servers are connected to and queries are executed in the order they appear in the configuration file.
Because of this, it is not advised to list too many servers as it can elongate the authentication process.

##### Configuration options

 * `connection_url`

   URL of the LDAP server which will be queried for user information and group
   membership.

 * `username`

   Optional username for LDAP bind, if not set bind with the login credentials
   will be attempted.

 * `password`

   Optional password for configured username.

 * `referrals`

   Microsoft Active Directory by returns referrals (search continuations).
   LDAPv3 does not specify which credentials should be used by the clients
   when chasing these referrals and will be tried as an anonymous access by
   the libldap library which might fail. Will be disabled by default.

 * `deref`

   Configure how the alias dereferencing is done in libldap (valid values:
   `always`, `never`).

 * `accountBase`

   Root tree containing all the user accounts.

 * `accountScope`

   Scope of the search performed. Accepted values are: base, one, subtree.

 * `accountPattern`

   The special `$USN$` token in the query is replaced to the *username* at
   login. Query pattern used to search for a user account. Must be a valid
   LDAP query expression.

   Example configuration: `(&(objectClass=person)(sAMAccountName=$USN$))`

 * `groupBase`

   Root tree containing all the groups.

 * `groupPattern`

   Group query pattern used. Must be a valid LDAP query expression.

 * `groupMemberPattern`

  Group member pattern will be combined with the group patten to query user
  for ldap group membership. `$USERDN$` will be automatically replaced by the
  queried user account DN.

  Example configuration: `(member=$USERDN$)`

 * `groupScope`

  Scope of the search performed. (Valid values are: `base`, `one`, `subtree`)

~~~{.json}
"method_ldap": {
  "enabled" : true,
  "authorities": [
    {
      "connection_url": "ldap://ldap.example.org",
      "username" : null,
      "password" : null,
      "referrals" : false,
      "deref" : "always",
      "accountBase" : null,
      "accountScope" : "subtree",
      "accountPattern" : "(&(objectClass=person)(sAMAccountName=$USN$))",
      "groupBase" : null,
      "groupScope" : "subtree",
      "groupPattern" : "(&(objectClass=group)(name=mygroup))",
      "groupMemberPattern" : "(member=$USERDN$)"
    },
    {
      "connection_url" : "ldaps://secure.internal.example.org:636",
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
      "groupMemberPattern" : null
    }
  ]
}
~~~

----

## Clientside configuration

### Web-browser client

Authentication in the web browser is handled via standard *HTTP Authenticate* headers, the browser will prompt the user to supply their crendentials.

For browser authentication to work, cookies must be enabled!

### Command-line client

The `CodeChecker cmd` client needs to be authenticated for a server before any data communication could take place.

The client's configuration file is expected to be at `~/.codechecker_passwords.json`, which is created at the first command executed
by using the package's `config/session_client.json` as an example.

> Please make sure, as a security precaution, that **only you** are allowed to access this file.
> Executing `chmod 0600 ~/.codechecker_passwords.json` will limit access to your user only.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd login [-h] [--host HOST] -p PORT [-u USERNAME]
                             [-pw PASSWORD] [-d]

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           Server host.
  -p PORT, --port PORT  HTTP Server port.
  -u USERNAME, --username USERNAME
                        Username to use on authentication (default: logged in user)
  -d, --deactivate, --logout
                        Send a logout request for the server
~~~~~~~~~~~~~~~~~~~~~

The user can log in onto the server by issuing the command `CodeChecker cmd login -h host -p port -u username -pw passphrase`.
After receiving an *Authentication successful!* message, access to the analysis information is given; otherwise, *Invalid access* is shown instead of real data.

Privileged session expire after a set amount of time. To log out manually, issue the command `CodeChecker cmd login -h host -p port --logout`.

#### Preconfigured credentials

To alleviate the need for supplying authentication in the command-line every time a server is connected to, users can pre-configure their credentials to be used in authentication.

To do so first copy the `config/session_client.json` file from the CodeChecker package to your home directory and rename it to `codechecker_passwords.json`
After creating the new file open `~/.codechecker_passwords.json`.

The `credentials` section is used by the client to read pre-saved authentication data in `username:password` format.

~~~{.json}
  "credentials": {
    "*" : "global:passphrase",
    "*:8080" : "webserver:1234",
    "localhost" : "local:admin",
    "localhost:6251" : "super:secret"
  },
~~~

Credentials are matched for any particular server at login in the following order:

  1. An exact `host:port` match is tried
  2. Matching for the `host` (on any port) is tried
  3. Matching for a particular port (on any host address), in the form of `*:port`, is tried
  4. Global credentials for the installation is stored with the `*` key

#### Automatic login

If authentication is required by the server and the user hasn't logged in but there are saved credentials for the server, `CodeChecker cmd` will automatically try to log in.

This behaviour can be disabled by setting `client_autologin` to `false`.

#### Currently active tokens

The user's currently active sessions' token are stored in the `~/.codechecker_USERNAME.session.json`.
