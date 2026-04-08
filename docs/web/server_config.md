CodeChecker server configuration
====================================

The server's configuration is stored in the server's *workspace* folder, in
`server_config.json`. This file is created, at the first start of the server,
using the package's installed `config/server_config.json` as a template.

> **NOTICE!** `session_config.json` file has been deprecated.

Table of Contents
=================
* [Task handling](#task-handling)
  * [Number of API worker processes](#number-of-api-worker-processes)
  * [Number of task worker processes](#number-of-task-worker-processes)

* [Run limitation](#run-limitations)
* [Storage](#storage)
  * [Directory of analysis statistics](#directory-of-analysis-statistics)
  * [Limits](#Limits)
    * [Maximum size of failure zips](#maximum-size-of-failure-zips)
    * [Size of the compilation database](#size-of-the-compilation-database)
  * [Keepalive](#keepalive)
    * [Idle time](#idle-time)
    * [Interval time](#interval-time)
    * [Probes](#probes)
* [Authentication](#authentication)
* [Secrets](#secrets)
  * [server_secrets.json](#server_secretsjson)
  * [Environmental variables](#environmental-variables)

## Task handling

### Number of API worker processes
The `worker_processes` section of the config file controls how many processes
will be started on the server to process API requests.

*Default value*: <CPU count>

The server needs to be restarted if the value is changed in the config file.

### Number of task worker processes
The `background_worker_processes` section of the config file controls how many
processes will be started on the server to process background jobs.

*Default value*: Fallback to same amount as `worker_processes`.

The server needs to be restarted if the value is changed in the config file.

### `--machine-id`
Unfortunately, servers don't always terminate gracefully (cue the aforementioned
`SIGKILL`, but also the container, VM, or the host machine could simply die
during execution, in ways the server is not able to handle). Because tasks are
not shared across server processes, and there are crucial bits of information in
the now dead process's memory which would have been needed to execute the task,
a server later restarting in place of a previously dead one should be able to
identify which tasks its "predecessor" left behind without clean-up.

This is achieved by storing the running computer's identifier, configurable via
`CodeChecker server --machine-id`, as an additional piece of information for
each task. By default, the machine ID is constructed from
`gethostname():portnumber`, e.g., `cc-server:80`.

In containerised environments, relying on `gethostname()` may not be entirely
stable! For example, Docker exposes the first 12 digits of the container's
unique hash as the _"hostname"_ of the insides of the container. If the
container is started with `--restart always` or `--restart unless-stopped`, then
this is fine, however, more advanced systems, such as _Docker swarm_ will
**create a new container** in case the old one died (!), resulting in a new
value of `gethostname()`.

In such environments, service administrators must pay additional caution and
configure their instances by setting `--machine-id` for subsequent executions of
the "same" server accordingly. If a server with machine ID **`M`** starts up
(usually after a container or "system" restart), it will set every task not in
any "termination states" and associated with machine ID **`M`** to the
_`DROPPED`_ status (with an appropriately formatted comment accompanying),
signifying that the _previous instance_ "dropped" these tasks, but had no chance
of recording this fact.

## Run limitation
The `max_run_count` section of the config file controls how many runs can be
stored on the server for a product.

If this field is not present in the config file or the value of this field is a
negative value, run storage becomes unlimited.

This option can be changed and reloaded without server restart by using the
`--reload` option of CodeChecker server command.

## Storage
The `store` section of the config file controls storage specific options for the
server and command line.

All sub-values of this option can be changed and reloaded without server restart
by using the `--reload` option of CodeChecker server command.

### Directory of analysis statistics
The `analysis_statistics_dir` option specifies a directory where analysis
statistics should be stored. If this option is specified in the config file the
client will send analysis related information to the server and the server will
store these information in this directory.
If this directory is not specified the server will not store any analysis
statistic information.

### Limits
The `limit` section controls limitation of analysis statistics.

#### Maximum size of failure zips
The `failure_zip_size` section of the `limit` controls the maximum size of
uploadable failure zips in *bytes*.

*Default value*: 52428800 bytes = 50 MB

#### Size of the compilation database
The `compilation_database_size` section of the `limit` controls the maximum
size of uploadable compilation database file in *bytes*.

*Default value*: 104857600 bytes = 100 MB

### Keepalive
Linux has built-in support for keepalive. When using a CodeChecker server
with `Docker Swarm` it is recommended to use the following settings:
```json
{
  "keepalive": {
    "enabled": true,
    "idle": 600,
    "interval": 30,
    "max_probe": 10
  }
}
```

Otherwise you may get a `[Errno 104] Connection reset by peer` exception on the
server side and the client may hang forever.

For more detailed information about these configuration option see:
https://tldp.org/HOWTO/TCP-Keepalive-HOWTO/usingkeepalive.html

For more information about this problem can be found here:
https://github.com/moby/moby/issues/31208#issuecomment-303905737

#### Idle time
The interval between the last data packet sent (simple ACKs are not considered
data) and the first keepalive probe.

By default the server will use the value from your host configured by the
`net.ipv4.tcp_keepalive_time` parameter. This value can be overriden by the
`idle` key in the server configuration file.

#### Interval time
The interval between subsequential keepalive probes, regardless of what the
connection has exchanged in the meantime.

By default the server will use the value from your host configured by the
`net.ipv4.tcp_keepalive_intvl` parameter. This value can be overriden by the
`interval` key in the server configuration file.

#### Probes
The number of unacknowledged probes to send before considering the connection
dead and notifying the application layer.

By default the server will use the value from your host configured by the
`net.ipv4.tcp_keepalive_probes` parameter. This value can be overriden by the
`max_probe` key in the server configuration file.

## Authentication
For authentication configuration options and which options can be reloaded see
the [Authentication](authentication.md) documentation.

## Secrets

### server_secrets.json
Optionally, one can store sensitive data (e.g., passwords, secret tokens) outside
of `server_config.json`. To do this, create a separate `server_secrets.json` file 
in the server's *workspace* folder. In `server_config.json`, replace sensitive data 
with `$SECRET:NAME_OF_SECRET$`.
Then, secrets can be defined in `server_secrets.json`, as an example:
```json
{
  "NAME_OF_SECRET": "MySecurePassword123"
}
```
Alternatively, one can also define entire sections as a secret, for instance:
```json
{
  "NAME_OF_SECRET": {
    "enabled" : true,
    "client_id" : "<ExampleClientID>",
    "client_secret": "<ExampleClientSecret>"
  }
}
```

### Environmental variables
Alternatively, CodeChecker can also read sensitive data from environmental variables.
To do this, replace sensitive data in `server_config.json` with `$ENV:VARIABLE_NAME$`.
In this case, value will be read from environmental variable `VARIABLE_NAME`.
