CodeChecker server configuration
====================================

The server's configuration is stored in the server's *workspace* folder, in
`server_config.json`. This file is created, at the first start of the server,
using the package's installed `config/server_config.json` as a template.

> **NOTICE!** `session_config.json` file has been deprecated.

Table of Contents
=================
* [Run limitation](#run-limitations)
* [Authentication](#authentication)

## Run limitation
The `max_run_count` section of the config file controls how many runs can be
stored on the server for a product.

If this field is not present in the config file or the value of this field is a
negative value, run storage becomes unlimited.

## Authentication
For authentication configuration options see the
[Authentication](authentication.md) documentation.
