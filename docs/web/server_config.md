CodeChecker server configuration
====================================

The server's configuration is stored in the server's *workspace* folder, in
`server_config.json`. This file is created, at the first start of the server,
using the package's installed `config/server_config.json` as a template.

> **NOTICE!** `session_config.json` file has been deprecated.

Table of Contents
=================
* [Run limitation](#run-limitations)
* [Storage](#storage)
  * [Directory of analysis statistics](#directory-of-analysis-statistics)
  * [Limits](#Limits)
    * [Maximum size of failure zips](#maximum-size-of-failure-zips)
    * [Size of the compilation database](#size-of-the-compilation-database)
* [Authentication](#authentication)

## Number of worker processes
The `worker_processes` section of the config file controls how many processes
will be started on the server to process API requests.

*Default value*: <CPU count>

The server needs to be restarted if the value is changed in the config file.

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
