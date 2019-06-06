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

*Default value*: 10

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

## Authentication
For authentication configuration options and which options can be reloaded see
the [Authentication](authentication.md) documentation.
