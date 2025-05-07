CodeChecker authentication subsystem
====================================

CodeChecker also supports only allowing a privileged set of users to access
the results stored on a server.

> **NOTICE!** Some authentication subsystems require additional packages to
> be installed before they can be used. See below.

Table of Contents
=================
* [Server-side configuration](#server-side-configuration)
    * [<i>Dictionary</i> authentication](#dictionary-authentication)
    * [External authentication methods](#external-auth-methods)
        * [<i>PAM</i> authentication](#pam-authentication)
        * [<i>LDAP</i> authentication](#ldap-authentication)
            * [Configuration options](#configuration-options)
      * [Membership in custom groups with <i>regex_groups</i>](#regex_groups-authentication)
      * [<i>OAuth</i> authentication](#oauth-authentication)
        * [<i>OAuth</i> Configuration options](#oauth-configuration-options)
        * [<i>OAuth</i> details per each provider](#oauth-details-per-each-provider)
* [Client-side configuration](#client-side-configuration)
    * [Web-browser client](#web-browser-client)
    * [Command-line client](#command-line-client)
        * [Preconfigured credentials](#preconfigured-credentials)
        * [Automatic login](#automatic-login)
        * [Currently active tokens](#currently-active-tokens)
* [Personal access token](#personal-access-token)
    * [`new`](#new-personal-access-token)
    * [`list`](#list-personal-access-token)
    * [`del`](#remove-personal-access-token)

# Server-side configuration <a name="server-side-configuration"></a>

The server's configuration is stored in the server's *workspace* folder, in
`server_config.json`. This file is created, at the first start of the server,
using the package's installed `config/server_config.json` as a template.

The `authentication` section of the config file controls how authentication
is handled.

 * `enabled`

    Setting this to `false` disables privileged access

 * `realm_name`

    The name to show for web-browser viewers' pop-up login window via
    *HTTP Authenticate*

 * `realm_error`

    The error message shown in the browser when the user fails to authenticate

 * `logins_until_cleanup`

    After this many login attempts made towards the server, it will perform an
    automatic cleanup of old, expired sessions.
    This option can be changed and reloaded without server restart by using the
    `--reload` option of CodeChecker server command.

 * `session_lifetime`

    (in seconds) The lifetime of the session sets that after this many seconds
    since last session access the session is permanently invalidated.

    This option can be changed and reloaded without server restart by using the
    `--reload` option of CodeChecker server command.

 * `refresh_time`

    (in seconds) Refresh time of the local session objects. We use local session
    to prevent huge number of queries to the database. These sessions are stored
    in the memory so if multiple CodeChecker servers use the same configuration
    database these should be synced with each other and with the database. This
    option defines the lifetime of the local session sets that after this many
    seconds since last session access the local session is permanently
    invalidated.

    This option can be changed and reloaded without server restart by using the
    `--reload` option of CodeChecker server command.
If the server is shut down, every session is **immediately** invalidated. The
running sessions are only stored in the server's memory, they are not written
to storage.

Every authentication method is its own JSON object in this section. Every
authentication method has its own `enabled` key which dictates whether it is
used at live authentication or not.

Users are authenticated if **any** authentication method successfully
authenticates them. Authentications are attempted in the order they are
described here: *dicitonary* takes precedence, *pam* is a secondary and *ldap*
is a tertiary backend, if enabled.

Only `refresh_time`, `session_lifetime` and `logins_until_cleanup` options can
be changed and reloaded without server restart by using the `--reload`
option of `CodeChecker server` command.

## <i>Dictionary</i> authentication <a name="dictionary-authentication"></a>

> *Note*: Storing passwords in a plain text file is *strongly discouraged* due to security risks. If no other option is available, ensure that the file permissions are restricted to 0600 to limit access *only* to the file owner.

The `authentication.method_dictionary` contains a plaintext `username:password`
credentials for authentication. If the user's login matches any of the
credentials listed, the user will be authenticated.

Groups are configured in a map which maps to each username the list of groups
the user belongs to.

~~~{.json}
"method_dictionary": {
  "enabled" : true,
  "auths" : [
      "global:admin",
      "test:test"
  ],
  "groups" : {
      "global" : ["admin", "guest"],
      "test" : ["guest"]
  }
}
~~~

## External authentication methods <a name="external-auth-methods"></a>

External authentication methods connect to a privilege manager to authenticate
users against.

Using external authentication methods - such as *PAM* or *LDAP* - require
additional packages and libraries to be installed on the system.

~~~{.sh}
# get additional system libraries
sudo apt-get install libldap2-dev libsasl2-dev libssl-dev

# the python virtual environment must be sourced!
source ~/checker_env/bin/activate

# install required python modules
pip3 install -r requirements_py/auth/requirements.txt
~~~

### <i>PAM</i> authentication <a name="pam-authentication"></a>

To access the server via PAM authentication, the user must provide valid
username and password which is accepted by PAM.

~~~{.json}
"method_pam": {
  "enabled" : true
}
~~~

The module can be configured to allow specific users or users belonging to
specific groups only. In the example below, `root` and `myname` can access the
server, and **everyone** who belongs to the `adm` or `cc-users` group can
access the server.

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

### <i>LDAP</i> authentication <a name="ldap-authentication"></a>

CodeChecker also supports *LDAP*-based authentication. The
`authentication.method_ldap` section contains the configuration for LDAP
authentication: the server can be configured to connect to as much
LDAP-servers as the administrator wants. Each LDAP server is identified by
a `connection_url` and a list of `queries` to attempt to log in the username
given.

Servers are connected to and queries are executed in the order they appear in
the configuration file. Because of this, it is not advised to list too many
servers as it can elongate the authentication process.

#### Configuration options <a name="configuration-options"></a>

 * `connection_url`

   URL of the LDAP server which will be queried for user information and group
   membership.

 * `tls_require_cert`

   If set to `never`, skip verification of certificate in LDAPS connections
   (!!! INSECURE !!!).

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

 * `user_dn_postfix_preference`

    User DN postfix preference value can be used to select out one prefered
    user DN if multiple DN entries are found by the LDAP search.
    The configured value will be matched and the first matching will be used.
    If only one DN was found this postfix matching will not be used.
    If not set and multiple values are found the first value
    in the search result list will be used.

   Example configuration: `OU=people,DC=example,DC=com`

 * `groupBase`

   Root tree containing all the groups.

 * `groupPattern`

   Group query pattern used LDAP query expression to find the group objects
   a user is a member of. It must contain a `$USERDN$` pattern.
   `$USERDN$` will be automatically replaced by the queried user account DN.

 * `groupNameAttr`

   The attribute of the group object which contains the name of the group.

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
      "user_dn_postfix_preference": null,
      "groupBase" : null,
      "groupScope" : "subtree",
      "groupPattern" : "(&(objectClass=group)(member=$USERDN$))",
      "groupNameAttr" : "sAMAccountName"
    },
    {
      "connection_url"   : "ldaps://secure.internal.example.org:636",
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
}
~~~

## Membership in custom groups with <a name="regex_groups-authentication">regex_groups</a>

Many regular expressions can be listed to define a group. Please note that the
regular expressions are searched in the whole username string, so they should
be properly anchored if you want to match only in the beginning or in the
end. Regular expression matching follows the rules of Python's
[re.search()](https://docs.python.org/3/library/re.html).

The following example will create a group named `everybody` that contains
every user regardless of the authentication method, and a group named `admins`
that contains the user `admin` and all usernames starting with `admin_` or
ending with `_admin`.

~~~{.json}
"regex_groups": {
  "enabled" : true,
  "groups" : {
      "everybody" : [ ".*" ],
      "admins"    : [ "^admin$", "^admin_", "_admin$" ]
  }
}
~~~

When we manage permissions on the GUI we can give permission to these
groups. For more information [see](permissions.md#managing-permissions).

----

### <i>OAuth</i> authentication <a name="oauth-authentication"></a>

CodeChecker also supports OAuth-based authentication. The `authentication.method_oauth` section contains the configuration for OAuth authentication for different OAuth providers. The server can be configured for different Oauth `providers`.
Specific behavior related to each provider is configured by a provider `template`. In addition to default values, the template supplies the parsing logic for the individual OAuth responses.

#### OAuth Configuration options <a name="oauth-configuration-options"></a>
  * `enabled`

    Indicates if OAuth authentication is enabled (required for any methods below)

  * `shared_variables`

      A key-value table that is used to set variables across all providers, for convenience.
      If using the `host` variable, it should be in the format `http://example.com`, including the protocol.

 * `providers`

    The provider field contains configuration details for OAuth providers. Each provider's configuration includes but may vary depending on provider:

  * `provider_name` as an object containing following properties:

      * `enabled`

          Indicates if current provider is enabled (github, google, etc.)

      * `client_id`

           Contains client ID provided by the OAuth provider.

      * `client_secret`

          The client secret must be provided by the OAuth provider.

      * `variables`

          A key-value table that is used to set variables used inside parameters.  
          To use a variable, specify it using `{variable}`.
          The `{provider}` variable is automatically set.

          Template `ms_entra/v2.0` uses the `{tenant_id}` variable.

      * `template`

          A configuration preset that applies default values and special handling for each available OAuth provider.
          Available values are `github/v1`, `google/v1`, and `ms_entra/v2.0`.

          If a template is specified, you most likely do not need to specify any other `url` option.

          **Note**: Specifying no template is currently not supported.

      * `callback_url`

          User will be redirected back to the provided link after login with returned data.
          It should be constructed in that format `{host}/login/OAuthLogin/{provider}` where the `host` variable includes the protocol used by the website. The `callback_url` should also match the callback url specified in the provider's configuration.
          You can use the variables `{host}` and `{provider}` for convenience.

          *Default*: `{host}/login/OAuthLogin/{provider}`

          Examples of specifying the correct link
          * `http://localhost:8080/login/OAuthLogin/{provider}`
          * `https://example.com/login/OAuthLogin/google`
          * `{host}/login/OAuthLogin/{provider}` (where `host` is set as `https://example.com`)

      * `authorization_url`

          This link is used for redirecting user for provider's authentication page.

          *Default*: Set by template.

      * `token_url`

          The URL to exchange the authorization code for an access token.

          *Default*: Set by template.

      * `user_info_url`

          The URL to fetch the authenticated user's information.

          *Default*: Set by template.

      * `user_emails_url`

          `GitHub` specific field to make requests for emails associated with github account.

          *Default*: Set by template.

      * `user_groups_url`

          `Microsoft`-specific field used to request security groups that the user is member of.

          *Default*: Set by template.

      * `jwks_url`

          `Microsoft`-specific field used to request public signing keys for decoding JWT tokens.

          *Default*: Set by template.

      * `scope`

          The scope of access requested from the OAuth provider.

          *Default*: Set by template.

      * `user_info_mapping`

          A mapping of user info fields from the provider to local fields.

          * `username`

              Field for the username.

        The `username` field defines what value will be used as the user's unique identifier (i.e. their "username") depending on the OAuth provider.

        Currently there are only 2 options for this:
         * `username`
         * `email` (*default*)

        Expected output for each provider:

        `github/v1`
          * `username` - user's GitHub `login` will be user's identifier
          * `email` - a request will be sent to fetch the primary email of account to be used as the user's identifier.
            If it is hidden, an error will be thrown.

        `google/v1`
          * Only supports `email`, and user's Gmail email will be considered his username.

        `ms_entra/v2.0`
          * `username` - Company's signum will be the user's identifier.
          * `email` - an email associated with this Microsoft account will be used as user's identifier.

    ### 🔧 Example: OAuth Configuration using templates
    
    ```jsonc
    "github": {
      "enabled": false,
      "client_id": "<ExampleClientID>",
      "client_secret": "<ExampleClientSecret>",
      "template": "github/v1",
      "user_info_mapping": { // optional
        "username": "username"
      }
    }
    ```

    ### 🔧 Example: OAuth Configuration for Microsoft

    ```jsonc
    "microsoft": {
      "enabled": false,
      "client_id": "<ExampleClientID>",
      "client_secret": "<ExampleClientSecret>",
      "template": "ms_entra/v2.0",
      "variables": {
        "tenant_id": "common" // replace with your own tenant ID, if not using multi-tenant mode
      },
      "user_info_mapping": { // optional
        "username": "email"
      }
    }
    ```

    ### 🔧 Example: OAuth Configuration without templates

    ```jsonc
    "google": {
      "enabled": false,
      "client_id": "<ExampleClientID>",
      "client_secret": "<ExampleClientSecret>",
      "template": "google/v1", // still needed for the response handling logic
      "authorization_url": "https://accounts.google.com/o/oauth2/auth",
      "callback_url": "https://<server_host>/login/OAuthLogin/google",
      "token_url": "https://accounts.google.com/o/oauth2/token",
      "user_info_url": "https://www.googleapis.com/oauth2/v1/userinfo",
      "scope": "openid email profile",
      "user_info_mapping": {
        "username": "email"
      }
    }
    ```

    For more information about the default values in templates, see [oauth_templates.py](../../web/codechecker_web/server/oauth_templates.py)



#### OAuth Details per each provider <a name ="oauth-details-per-each-provider"></a>

* Important: `callback_url` must always match with the link specified in the
providers' settings when issuing an OAuth application.

* Important: At the time this code was written, GitHub doesn't support PKCE (Proof Key for Code Exchange).
Therefore PKCE is not used when users log in using GitHub.


# Client-side configuration <a name="client-side-configuration"></a>

## Web-browser client <a name="web-browser-client"></a>

Authentication in the web browser is handled via standard *HTTP Authenticate*
headers, the browser will prompt the user to supply their credentials.

For browser authentication to work, cookies must be enabled!

## Command-line client <a name="command-line-client"></a>

The `CodeChecker cmd` client needs to be authenticated for a server before any
data communication could take place.

The client's configuration file is expected to be at
`~/.codechecker.passwords.json`, which is created at the first command executed
by using the package's `config/session_client.json` as an example.

> Please make sure, as a security precaution, that **only you** are allowed to
> access this file. Executing `chmod 0600 ~/.codechecker.passwords.json` will
> limit access to your user only.

<details>
  <summary>
    <i>$ <b>CodeChecker cmd login --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd login [-h] [-d] [--url SERVER_URL]
                             [--verbose {info,debug,debug_analyzer}]
                             [USERNAME]

Certain CodeChecker servers can require elevated privileges to access analysis
results. In such cases it is mandatory to authenticate to the server. This
action is used to perform an authentication in the command-line.

positional arguments:
  USERNAME              The username to authenticate with. (default: <username>)

optional arguments:
  -h, --help            show this help message and exit
  -d, --deactivate, --logout
                        Send a logout request to end your privileged session.

common arguments:
  --url SERVER_URL      The URL of the server to access, in the format of
                        '[http[s]://]host:port'. (default: localhost:8001)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.
```
</details>

The user can log in onto the server by issuing the command `CodeChecker cmd
login <username>`. After receiving an *Authentication successful!* message,
access to the analysis information is given; otherwise, *Invalid access* is
shown instead of real data.

Privileged session expire after a set amount of time. To log out manually,
issue the command `CodeChecker cmd login -d`.

### Preconfigured credentials <a name="preconfigured-credentials"></a>

To alleviate the need for supplying authentication in the command-line every
time a server is connected to, users can pre-configure their credentials to be
used in authentication.

To do so first copy the `config/session_client.json` file from the CodeChecker
package to your home directory and rename it to `.codechecker.passwords.json`
After creating the new file open `~/.codechecker.passwords.json`.

The `credentials` section is used by the client to read pre-saved
authentication data in `username:password` format.

```json
{
  "client_autologin" : true,
  "credentials": {
    "*" : "global:passphrase",
    "*:8080" : "webserver:1234",
    "localhost" : "local:admin",
    "localhost:6251" : "super:secret",
    "https://my.company.org:443": "user:pass"
  }
}
```

Credentials are matched for any particular server at login in the following
order:

  1. An exact `host:port` match is tried
  2. Matching for the `host` (on any port) is tried
  3. Matching for a particular port (on any host address), in the form of
     `*:port`, is tried
  4. Global credentials for the installation is stored with the `*` key

Is it possible to generate a token from command line which can be used to
authenticate in the name of the given user. This way no need to store passwords
in text files. For more information [see](#personal-access-token).

The location of the password file can be configured by the `CC_PASS_FILE`
environment variable. This environment variable can also be used to setup
different credential files to login to the same server with a different user.

Furthermore, the location of the session file can be configured by the
`CC_SESSION_FILE` environment variable. This can be useful if CodeChecker does
not have the permission to create a session file under the user's home
directory (e.g. in some CI environments).

### Automatic login <a name="automatic-login"></a>

If authentication is required by the server and the user hasn't logged in but
there are saved credentials for the server, `CodeChecker cmd` will
automatically try to log in.

This behaviour can be disabled by setting `client_autologin` to `false`.

### Currently active tokens <a name="currently-active-tokens"></a>

The user's currently active sessions' token are stored in the
`~/.codechecker.session.json`.

# Personal access token <a name="personal-access-token"></a>
Command line clients can authenticate itself using the username/password stored
in the [`.codechecker.passwords.json`](#preconfigured-credentials). It is
obviously not a good idea to store passwords in text files. Instead of this the
user is able to generate a token from command line, that can be used to
authenticate in the name of his/her name.

**Note**: To generate a new token, the user **must be logged in** first. Use
the `CodeChecker cmd login` command for it. After you have successfully logged
in you can generate a new token with the `CodeChecker cmd token new` command.

Personal tokens can be written instead of the user's password in the
`~/.codechecker.passwords.json` file:
```json
{
  "client_autologin" : true,
  "credentials": {
    "*" : "global:passphrase",
    "localhost:6251" : "super:22eca8f31ad117e90c371f2e98bcf4c9",
    "https://my.company.org:443": "user:pass"
  }
}
```

## New personal access token <a name="new-personal-access-token"></a>
<details>
  <summary>
    <i>$ <b>CodeChecker cmd token new --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd token new [-h] [--description DESCRIPTION]
                                 [--url SERVER_URL]
                                 [--verbose {info,debug,debug_analyzer}]
                                 NAME

Creating a new personal access token.

positional arguments:
  NAME                  A unique name that identifies the access token.

options:
  -h, --help            show this help message and exit
  --description DESCRIPTION
                        A custom textual description to be shown alongside the
                        token.

common arguments:
  --url SERVER_URL      The URL of the server to access, in the format of
                        '[http[s]://]host:port'. (default: localhost:8001)
  --verbose {info,debug_analyzer,debug}
                        Set verbosity level.
```
</details>

## List personal access tokens <a name="list-personal-access-token"></a>
<details>
  <summary>
    <i>$ <b>CodeChecker cmd token list --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd token list [-h] [--url SERVER_URL]
                                  [-o {plaintext,html,rows,table,csv,json}]
                                  [--verbose {info,debug,debug_analyzer}]

List the available personal access tokens.

options:
  -h, --help            show this help message and exit
  -o {plaintext,rows,table,csv,json}, --output {plaintext,rows,table,csv,json}
                        The output format(s) to use in showing the data. Mind
                        that some output formats are (like 'json') more verbose
                        than others (like 'plaintext'). (default: plaintext)

common arguments:
  --url SERVER_URL      The URL of the server to access, in the format of
                        '[http[s]://]host:port'. (default: localhost:8001)
  --verbose {info,debug_analyzer,debug}
                        Set verbosity level.
```
</details>

## Remove personal access token <a name="remove-personal-access-token"></a>
<details>
  <summary>
    <i>$ <b>CodeChecker cmd token del --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd token del [-h] [--url SERVER_URL]
                                 [--verbose {info,debug,debug_analyzer}]
                                 NAME

Removes the specified access token.

positional arguments:
  NAME                  Name of the personal access token that will be deleted.

options:
  -h, --help            show this help message and exit

common arguments:
  --url SERVER_URL      The URL of the server to access, in the format of
                        '[http[s]://]host:port'. (default: localhost:8001)
  --verbose {info,debug_analyzer,debug}
                        Set verbosity level.
```
</details>
