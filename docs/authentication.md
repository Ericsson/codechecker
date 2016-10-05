CodeChecker authentication subsytem
===================================

# Please be advised, that currently, login credentials travel on an unencrypted channel!

CodeChecker also supports only allowing a privileged set of users to access the results stored on a server.

> **NOTICE!** Some authentication subsystems require additional packages to be installed before they can be used.
 
## Serverside configuration

The server's configuration is stored in the server's *workspace* folder, in `session_config.json`.
This file is created, at the first start of the server, using the package's installed `config/session_config.json` as a template.
 
The `authentication` section of the config file controls how authentication is handled.

 * `enabled`  
    setting this to `false` disables privileged access
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

Users are authenticated if **any** authentication method successfully authenticates them. If both methods are enabled, *dictionary* authentication takes precedence.

### *Dictionary* authentication

The `authentication.method_dictionary` contains a plaintext `username:password` credentials for authentication.
If the user's login matches any of the credentials listed, the user will be authenticated.

```json
"method_dictionary": {
  "enabled" : true,
  "auths" : [
      "global:admin",
      "test:test"
  ]
}
```

### *LDAP* authentication

#### Prerequisites

Using the *LDAP* authentication requires some additional packages to be installed on the system.

~~~~~~{.sh}

# get additional system libraries
sudo apt-get install libldap2-dev libsasl2-dev libssl-dev

# the python virtual environment must be sourced!
source ~/checker_env/bin/activate

# install required basic python modules
pip install python-ldap
~~~~~~

#### Settings

CodeChecker also supports *LDAP*-based authentication. The `authentication.method_ldap` section contains the configuration for LDAP authentication:
the server can be configured to connect to as much LDAP-servers as the administrator wants. Each LDAP server is identified by a `connection_url` and a list of `queries`
to attempt to log in the username given.

Servers are connected to and queries are executed in the order they appear in the configuration file.
Because of this, it is not advised to list too many servers as it can elongenate the authentication process.

The special `$USN$` token in the query is replaced to the *username* at login.

```json
"method_ldap": {
  "enabled" : true,
  "authorities": [
    {
      "connection_url": "ldap://ldap.example.org",
      "queries": [
        "uid=$USN$,ou=admins,o=mycompany"
      ]
    },
    {
      "connection_url" : "ldaps://secure.internal.example.org:636",
      "queries": [
        "uid=$USN$,ou=owners,ou=secure,o=company"
      ]
    }
  ]
}
```

----

## Clientside configuration

### Web-browser client

Authentication in the web browser is handled via standard *HTTP Authenticate* headers, the browser will prompt the user to supply their crendentials.

For browser authentication to work, cookies must be enabled!

### Command-line client

The `CodeChecker cmd` client needs to be authenticated for a server before any data communication could take place.

The client's configuration file is expected to be at `~/.codechecker_passwords.json`, which is created at the first command executed
by using the package's `config/session_client.json` as an example.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd login [-h] [--host HOST] -p PORT [-u USERNAME]
                             [-pw PASSWORD] [-d]

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           Server host.
  -p PORT, --port PORT  HTTP Server port.
  -u USERNAME, --username USERNAME
                        Username to use on authentication
  -pw PASSWORD, --password PASSWORD
                        Password for username-password authentication
                        (optional)
  -d, --deactivate, --logout
                        Send a logout request for the server
~~~~~~~~~~~~~~~~~~~~~

The user can log in onto the server by issuing the command `CodeChecker cmd login -h host -p port -u username -pw passphrase`.
After receiving an *Authentication successful!* message, access to the analysis information is given; otherwise, *Invalid access* is shown instead of real data.

Privileged session expire after a set amount of time. To log out manually, issue the command `CodeChecker cmd login -h host -p port --logout`.

#### Preconfigured credentials

To alleviate the need for supplying authentication in the command-line every time a server is connected to, users can pre-configure their credentials to be used in authentication.

To do so, open `~/.codechecker_passwords.json`. The `credentials` section is used by the client to read pre-saved authentication data in `username:password` format.

```json
  "credentials": {
    "*" : "global:passphrase",
    "*:8080" : "webserver:1234",
    "localhost" : "local:admin",
    "localhost:6251" : "super:secret"
  },
```

Credentials are matched for any particular server at login in the following order:

  1. An exact `host:port` match is tried
  2. Matching for the `host` (on any port) is tried
  3. Matching for a particular port (on any host address), in the form of `*:port`, is tried
  4. Global credentials for the installation is stored with the `*` key

#### Automatic login

If authentication is required by the server and the user hasn't logged in but there are saved credentials for the server, `CodeChecker cmd` will automatically try to log in.

This behaviour can be disabled by setting `client_autologin` to `false`.

#### Currently active tokens

The user's currently active sessions' token are stored in the `/tmp/.codechecker_USERNAME.session.json` (where `/tmp` is the environment's *temp* folder) file.
