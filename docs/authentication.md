CodeChecker authentication subsytem
===================================
 
CodeChecker also supports only allowing a privileged set of users to access the results stored on a server.
Authentication configuration is stored in the `config/session_config.json` file for the server and a template in `config/session_client.json` for the client.
The user's own configuration is copied by the client &ndash; at first launch &ndash; to `~/.codechecker_passwords.json`.
 
## Serverside configuration
 
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

Users are authenticated if **any** authentication method successfully authenticates them.

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

### `LDAP` authentication

> TBD

----

## Clientside configuration

### Web-browser client

Authentication in the web browser is handled via standard *HTTP Authenticate* headers, the browser will prompt the user to supply their crendentials.

For browser authentication to work, cookies must be enabled!

### Command-line client

The `CodeChecker cmd` client needs to be authenticated for a server before any data communication could take place.

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

The configuration file's `tokens` section contains the user's currently active sessions' tokens. This is not meant to be edited by hand, the client manages this section.