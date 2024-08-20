# CodeChecker Web Command Line User Guide

## Table of Contents
- [CodeChecker Web Command Line User Guide](#codechecker-web-command-line-user-guide)
  - [Table of Contents](#table-of-contents)
  - [Command Line Overview](#command-line-overview)
  - [WEB related sub-commands](#web-related-sub-commands)
    - [Client side configuration file](#client-side-configuration-file)
    - [`server`](#server)
      - [Creating a public server](#creating-a-public-server)
      - [Run CodeChecker server in Docker](#run-codechecker-server-in-docker)
      - [Configuring database and server settings location](#configuring-database-and-server-settings-location)
        - [Server Configuration (Authentication and Server Limits)](#server-configuration-authentication-and-server-limits)
        - [Database Configuration](#database-configuration)
      - [Initial super-user](#initial-super-user)
      - [Enfore secure socket (TLS/SSL)](#enfore-secure-socket-tlsssl)
      - [Managing running servers](#managing-running-servers)
      - [Manage server database upgrades](#manage-server-database-upgrades)
    - [`store`](#store)
      - [Format of `PRODUCT_URL`](#format-of-product_url)
      - [Example](#example)
    - [`cmd`](#cmd)
      - [Source components (`components`)](#source-components-components)
        - [New/Edit source component](#newedit-source-component)
          - [Format of component file](#format-of-component-file)
        - [List source components](#list-source-components)
        - [Delete source components](#delete-source-components)
      - [List runs (`runs`)](#list-runs-runs)
      - [List of run histories (`history`)](#list-of-run-histories-history)
      - [List analysis results' summary (`results`)](#list-analysis-results-summary-results)
        - [Example](#example-1)
      - [Show differences between two runs (`diff`)](#show-differences-between-two-runs-diff)
      - [Show summarised count of results (`sum`)](#show-summarised-count-of-results-sum)
        - [Summary Example](#summary-example)
      - [Remove analysis runs (`del`)](#remove-analysis-runs-del)
      - [Update an analysis run (`update`)](#update-an-analysis-run-update)
      - [Import suppressions (`suppress`)](#import-suppressions-suppress)
        - [Import suppressions from a suppress file](#import-suppressions-from-a-suppress-file)
      - [Manage product configuration of a server (`products`)](#manage-product-configuration-of-a-server-products)
      - [Query authorization settings (`permissions`)](#query-authorization-settings-permissions)
      - [Authenticate to the server (`login`)](#authenticate-to-the-server-login)
      - [Server-side task management (`serverside-tasks`)](#server-side-task-management-serverside-tasks)
    - [Exporting source code suppression to suppress file](#exporting-source-code-suppression-to-suppress-file)
      - [Export comments and review statuses (`export`)](#export-comments-and-review-statuses-export)
      - [Import comments and review statuses into Codechecker (`import`)](#import-comments-and-review-statuses-into-codechecker-import)
    - [`version`](#version)
      - [JSON format](#json-format)
  - [Log Levels](#log-levels)

## Command Line Overview

CodeChecker command line interface consists of **analysis** and **web** related
sub-commands.

This user guide describes **web server and client** related sub commands
to perform the following actions:
* [Start & Manage CodeChecker web server instances](#server)
* [Store/Read/Manage analysis results](#store)
* [Calculate diff between runs](#show-differences-between-two-runs-diff)
* [Configure codechecker repositories (products)](#manage-product-configuration-of-a-server-products)
* [Configure source code components](#source-components-components)
* [Use suppression files (instead of in-line suppressions)](#import-suppressions-suppress)
* [Export/Import Suppression Rules and Comments](#exporting-source-code-suppression-to-suppress-file)

The CodeChecker client uses only HTTP(S) protocol to communicate with the
server.

Running CodeChecker is via its main invocation script, `CodeChecker`:

<details>
  <summary><i>$ <b>CodeChecker --help</b> (click to expand)</i></summary>

```
usage: CodeChecker [-h]
                   {analyze,analyzers,check,checkers,cmd,log,parse,server,store,version}
                   ...

Run the CodeChecker sourcecode analyzer framework.
Please specify a subcommand to access individual features.

positional arguments:
  {analyze,analyzers,check,checkers,cmd,log,parse,server,store,version}
                        commands

    analyze             Execute the supported code analyzers for the files
                        recorded in a JSON Compilation Database.
    analyzers           List supported and available analyzers.
    check               Perform analysis on a project and print results to
                        standard output.
    checkers            List the checkers available for code analysis.
    cmd                 View analysis results on a running server from the
                        command line.
    log                 Run a build command and collect the executed
                        compilation commands, storing them in a JSON file.
    parse               Print analysis summary and results in a human-readable
                        format.
    server              Start and manage the CodeChecker Web server.
    store               Save analysis results to a database.
    version             Print the version of CodeChecker package that is being
                        used.

optional arguments:
  -h, --help            show this help message and exit
```
</details>

## WEB related sub-commands

### Client side configuration file

CodeChecker command line invocation parameter list can be long.

All CodeChecker sub-command can use a `--config CONFIG_FILE` to describe
command line argument lists.

For example instead of invoking
`CodeChecker store --name my_run --tag=my_tag --url=http://codechecker.my:9090/MyProduct`

one can write `CodeChecker store --config client_config.json`.

`client_config.json`
```json
{
  "store": [
    "--name=my_run",
    "--tag=my_tag",
    "--url=http://codechecker.my:9090/MyProduct"
  ]
}
```
For details see [Client Configuration File](config_file.md)

### `server`

To view and store the analysis reports in a database, a `CodeChecker server`
must be started. This is done via the `server` command, which creates a
standard Web server and initializes or connects to a database with
the given configuration.

The CodeChecker Viewer server can be browsed by a Web browser by opening the
address of it (by default, [`http://localhost:8001`](http://localhost:8001)),
or via the `CodeChecker cmd` command-line client.

<details>
  <summary><i>$ <b>CodeChecker server --help</b> (click to expand)</i></summary>

```
usage: CodeChecker server [-h] [-w WORKSPACE] [-f CONFIG_DIRECTORY]
                          [--machine-id MACHINE_ID]  [--host LISTEN_ADDRESS]
                          [-v PORT] [--not-host-only] [--skip-db-cleanup]
                          [--config CONFIG_FILE]
                          [--sqlite SQLITE_FILE | --postgresql]
                          [--dbaddress DBADDRESS] [--dbport DBPORT]
                          [--dbusername DBUSERNAME] [--dbname DBNAME]
                          [--force-authentication]
                          [-l | -r | -s | --stop-all]
                          [--db-status STATUS | --db-upgrade-schema PRODUCT_TO_UPGRADE | --db-force-upgrade]
                          [--verbose {info,debug,debug_analyzer}]

The CodeChecker Web server is used to handle the storage and navigation of
analysis results. A started server can be connected to via a Web browser, or
by using the 'CodeChecker cmd' command-line client.

optional arguments:
  -h, --help            show this help message and exit
  -w WORKSPACE, --workspace WORKSPACE
                        Directory where CodeChecker can store analysis result
                        related data, such as the database. (Cannot be
                        specified at the same time with '--sqlite' or
                        '--config-directory'.) (default:
                        /home/<username>/.codechecker)
  -f CONFIG_DIRECTORY, --config-directory CONFIG_DIRECTORY
                        Directory where CodeChecker server should read server-
                        specific configuration (such as authentication
                        settings, and TLS/SSL certificates) from.
                        (default: /home/<username>/.codechecker)
  --machine-id MACHINE_ID
                        A unique identifier to be used to identify the machine
                        running subsequent instances of the "same" server
                        process. This value is only used internally to
                        maintain normal function and bookkeeping of executed
                        tasks following an unclean server shutdown, e.g.,
                        after a crash or system-level interference. If
                        unspecified, defaults to a reasonable default value
                        that is generated from the computer's hostname, as
                        reported by the operating system. In most scenarios,
                        there is no need to fine-tune this, except if
                        subsequent executions of the "same" server is achieved
                        in distinct environments, e.g., if the server
                        otherwise is running in a container.
  --host LISTEN_ADDRESS
                        The IP address or hostname of the server on which it
                        should listen for connections. For IPv6 listening,
                        specify an IPv6 address, such as "::1". (default:
                        localhost)
  -v PORT, --view-port PORT, -p PORT, --port PORT
                        The port which will be used as listen port for the
                        server. (default: 8001)
  --not-host-only       If specified, storing and viewing the results will be
                        possible not only by browsers and clients running
                        locally, but to everyone, who can access the server
                        over the Internet. (Equivalent to specifying '--host
                        "::"'.) (default: False)
  --skip-db-cleanup     Skip performing cleanup jobs on the database like
                        removing unused files. (default: False)
  --config CONFIG_FILE  Allow the configuration from an explicit configuration
                        file. The values configured in the config file will
                        overwrite the values set in the command line.
                        You can use any environment variable inside this file
                        and it will be expaneded.
                        For more information see the docs: https://github.com/
                        Ericsson/codechecker/tree/master/docs/config_file.md
                        (default: None)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.

configuration database arguments:
  --sqlite SQLITE_FILE  Path of the SQLite database file to use. (default:
                        <CONFIG_DIRECTORY>/config.sqlite)
  --postgresql          Specifies that a PostgreSQL database is to be used
                        instead of SQLite. See the "PostgreSQL arguments"
                        section on how to configure the database connection.

PostgreSQL arguments:
  Values of these arguments are ignored, unless '--postgresql' is specified!

  --dbaddress DBADDRESS, --db-host DBADDRESS
                        Database server address. (default: localhost)
  --dbport DBPORT, --db-port DBPORT
                        Database server port. (default: 5432)
  --dbusername DBUSERNAME, --db-username DBUSERNAME
                        Username to use for connection. (default: codechecker)
  --dbname DBNAME, --db-name DBNAME
                        Name of the database to use. (default: config)
```
</details>

To start a server with default configuration, simply execute

```sh
CodeChecker server
```

#### Creating a public server

```
  --host LISTEN_ADDRESS
                        The IP address or hostname of the server on which it
                        should listen for connections. (default: localhost)
  --not-host-only       If specified, viewing the results will be possible not
                        only by browsers and clients running locally, but to
                        everyone, who can access the server over the Internet.
                        (Equivalent to specifying '--host ""'.) (default:
                        False)
```

By default, the running server can only be accessed from the same machine
(`localhost`) where it is running. This can be overridden by specifying
`--host ""`, instructing the server to listen on all available interfaces.


#### Run CodeChecker server in Docker
To run CodeChecker server in Docker see the [Docker](docker.md) documentation.

#### Configuring database and server settings location


CodeChecker server can use PostgreSQL or SQLite databases to store the analysis
results. SQLite is not recommended for high volume production usage,
only for small test installations.


##### Server Configuration (Authentication and Server Limits)

The `server_config.json` file describes
the run-time settings of the web server.

The following parameters can be configured
* Auhtentication methods (LDAP, File Based, PAM)
* Number of server threads
* Storage Limits:  Maximum number of runs, maximum failiure zip size etc.
* TCP related settings

You can find a specification of this file in
[Server Configuration](server_config.md) document and authentication
related sections in the [Authentication Configuration](authentication.md)
document.

The `--config-directory (-f)` specifies where the server configuration
files are located.

For example, one can start
two servers with two different product layout, but with the same
(authentication) configuration:

```sh
CodeChecker server --sqlite ~/major_bugs.sqlite -f ~/.codechecker -p 8001
CodeChecker server --sqlite ~/minor_bugs.sqlite -f ~/.codechecker -p 8002
```

If sqlite database is used, the `--workspace` argument can be used to _shortcut_
this specification. The configuration file and the sqlite files will be located
in the workspace directory.

##### Database Configuration

The `--sqlite` (or `--postgresql` and the various `--db-` arguments) can be
used to specify where the database, containing the analysis reports is located.

If the server is started in `--sqlite` mode and fresh, that is, no product
repository sqlite file is found, a product named `Default`, using `Default.sqlite`
in the configuration directory is automatically created. Please see
[Product management](products.md) for details on how to configure products.

In order to use PostgreSQL instead of SQLite, use the `--postgresql` command
line argument for `CodeChecker server` command.
If `--postgresql` is not given then SQLite is used by default in
which case `--dbport`, `--dbaddress`, `--dbname`, and
`--dbusername` command line arguments are ignored.

**NOTE!** Schema migration is not supported with SQLite. This means if you
upgrade your CodeChecker to a newer version, you might need to re-check your
project.

**It is recommended to use only the Postgresql databse for production
deployments!**

#### Initial super-user

You can give a single user SUPER_USER permission
by setting the `super_user` field in the `authentication`
section of the `server_config.json`.
The user which is set here, must be an existing user.
For example it should be a user
with dictionary authentication method.

```
 "authentication": {
    "enabled" : true,
    "super_user" : "admin",
...

```

#### Enfore secure socket (TLS/SSL)

You can enforce TLS/SSL security on your listening socket. In this case all clients
must access your server using the `https://host:port` URL format.

To enable TLS/SSL simply place a TLS certificate to `<CONFIG_DIRECTORY>/cert.pem`
and the corresponding private key to `<CONFIG_DIRECTORY>/key.pem`.
You can generate these certificates for example
using the [openssl tool](https://www.openssl.org/).
When the server finds these files upon start-up,
TLS/SSL will be automatically enabled.

#### Managing running servers

```
running server management:
  -l, --list            List the servers that has been started by you.
  -r, --reload          Sends the CodeChecker server process a SIGHUP signal,
                        causing it to reread it's configuration files.
  -s, --stop            Stops the server associated with the given view-port
                        and workspace.
  --stop-all            Stops all of your running CodeChecker server
                        instances.
```

CodeChecker servers can be started in the background as any other service, via
common shell tools such as `nohup` and `&!`. The running instances can be
queried via `--list`.

Calling `CodeChecker server --stop` will stop the "default" server, i.e. one
that was started by simply calling `CodeChecker server`. This _"stop"_ command
is equivalent to pressing `Ctrl`-`C` in the server's terminal, resulting in an
immediate termination of the server.

A server running on a specific and port can be stopped by:

```sh
CodeChecker server -w ~/my_codechecker_workspace -p 8002 --stop
```

`--stop-all` will stop every running server that is printed by `--list`.

`CodeChecker server --reload` command allows you to changing configuration-file
options that do not require a complete restart to take effect. For more
information which option can be reloaded see
[server config](server_config.md).

#### Manage server database upgrades

Use these arguments to manage the database versions handled by the server.
For a more detailed description about the schema upgrade check out the
[schema migration guide](db_schema_guide.md).

```
Database management arguments.:
  WARNING these commands needs to be called with the same workspace and
  configuration arguments as the server so the configuration database will
  be found which is required for the schema migration. Migration can be done
  without a running server but pay attention to use the same arguments which
  will be used to start the server. NOTE: Before migration it is advised to
  create a full a backup of the product databases.

  --status STATUS       Name of the product to get the database status for.
                        Use 'all' to list the database statuses for all of the
                        products.
  --upgrade-schema PRODUCT_TO_UPGRADE
                        Name of the product to upgrade to the latest database
                        schema available in the package. Use 'all' to upgrade
                        all of the products.NOTE: Before migration it is
                        advised to create a full backup of the product
                        databases.
  --db-force-upgrade    Force the server to do database migration without user
                        interaction. NOTE: Please use with caution and before
                        automatic migration it is advised to create a full
                        backup of the product databases.
```


### `store`

A `Codechecker server` needs to be started before the reports can be stored to
a database.

`store` is used to save previously created machine-readable analysis results
(such as `plist` files), usually previously generated by `CodeChecker analyze`
to the database.

<details>
  <summary><i>$ <b>CodeChecker store --help</b> (click to expand)</i></summary>

```
usage: CodeChecker store [-h] [-t {plist}] [-n NAME] [--tag TAG]
                         [--description DESCRIPTION]
                         [--trim-path-prefix [TRIM_PATH_PREFIX [TRIM_PATH_PREFIX ...]]]
                         [--config CONFIG_FILE] [-f] [--url PRODUCT_URL]
                         [--verbose {info,debug,debug_analyzer}]
                         [file/folder [file/folder ...]]

Store the results from one or more 'codechecker-analyze' result files in a
database.

positional arguments:
  file/folder           The analysis result files and/or folders containing
                        analysis results which should be parsed and printed.
                        If multiple report directories are given, OFF and
                        UNAVAILABLE detection statuses will not be available.
                        (default: /home/<username>/.codechecker/reports)

optional arguments:
  -h, --help            show this help message and exit
  -t {plist}, --type {plist}, --input-format {plist}
                        Specify the format the analysis results were created
                        as. (default: plist)
  -n NAME, --name NAME  The name of the analysis run to use in storing the
                        reports to the database. If not specified, the '--
                        name' parameter given to 'codechecker-analyze' will be
                        used, if exists.
  --tag TAG             A unique identifier for this individual store of results
                        in the run's history.
  --description DESCRIPTION
                        A custom textual description to be shown alongside the
                        run.
  --trim-path-prefix [TRIM_PATH_PREFIX [TRIM_PATH_PREFIX ...]]
                        Removes leading path from files which will be printed.
                        For instance if you analyze files
                        '/home/jsmith/my_proj/x.cpp' and
                        '/home/jsmith/my_proj/y.cpp', but would prefer to have
                        them displayed as 'my_proj/x.cpp' and 'my_proj/y.cpp'
                        in the web/CLI interface, invoke CodeChecker with '--
                        trim-path-prefix "/home/jsmith/"'.If multiple prefixes
                        is given, the longest match will be removed. You may
                        also use Unix shell-like wildcards (e.g.
                        '/*/jsmith/').
  --config CONFIG_FILE  Allow the configuration from an explicit configuration
                        file. The values configured in the config file will
                        overwrite the values set in the command line.
                        You can use any environment variable inside this file
                        and it will be expaneded.
                        For more information see the docs: https://github.com/
                        Ericsson/codechecker/tree/master/docs/config_file.md
                        (default: None)
  -f, --force           Delete analysis results stored in the database for the
                        current analysis run's name and store only the results
                        reported in the 'input' files. (By default,
                        CodeChecker would keep reports that were coming from
                        files not affected by the analysis, and only
                        incrementally update defect reports for source files
                        that were analysed.)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.

server arguments:
  Specifies a 'CodeChecker server' instance which will be used to store the
  results. This server must be running and listening, and the given product
  must exist prior to the 'store' command being run.

  --url PRODUCT_URL     The URL of the product to store the results for, in
                        the format of '[http[s]://]host:port/Endpoint'.
                        (default: localhost:8001/Default)

environment variables:
  CC_PASS_FILE     The location of the password file for auto login. By default
                   CodeChecker will use '~/.codechecker.passwords.json' file.
                   It can also be used to setup different credential files to
                   login to the same server with a different user.

  CC_SESSION_FILE  The location of the session file where valid sessions are
                   stored. This file will be automatically created by
                   CodeChecker. By default CodeChecker will use
                   '~/.codechecker.session.json'. This can be used if
                   restrictive permissions forbid CodeChecker from creating
                   files in the users home directory (e.g. in a CI
                   environment).

The results can be viewed by connecting to such a server in a Web browser or
via 'CodeChecker cmd'.
```
</details>

For example, if the analysis was run like:

```sh
CodeChecker analyze ../codechecker_myProject_build.log -o ./my_results
```

then the results of the analysis can be stored with this command:

```sh
CodeChecker store ./my_results -n my_project
```

#### Format of `PRODUCT_URL`

Several sub-commands, such as `store` and `cmd` need a connection specification
that identifies a server and a *Product* (read more [about
products](products.md)). Actions, like report storage or result
retrieving are performed on these targets.

This is done via the `PRODUCT_URL` where indicated in the subcommand, which
contains the server's access protocol, address, and the to-be-used product's
unique endpoint. The format of this string is:
`[http[s]://]host:port/ProductEndpoint`. This URL looks like a standard Web
browsing (HTTP) request URL.

CodeChecker communicates via HTTP requests, thus the first part specifies
whether or not a more secure SSL/TLS-wrapped `https` protocol should be used.
If omitted, the default value is `http`. The second part is the host and the
port the server listens on. After a `/`, the unique endpoint of the product
must be given, this is case-sensitive. This unique endpoint is configured and
allocated when the [product is created](products.md), by the server's
administrators. The product must exist and be properly configured before any
normal operation could be done on it.

If no URL is specified, the default value `http://localhost:8001/Default` will
be used: a standard HTTP CodeChecker server running on the local machine, on
the default port, using the *Default* product.

#### Example

The URL `https://codechecker.example.org:9999/SampleProduct` will access the
server machine `codechecker.example.org` trying to connect to a server
listening on port `9999` via HTTPS. The product `SampleProduct` will be used.


### `cmd`

The `CodeChecker cmd` is a lightweight command line client that can be used to
view analysis results from the command-line. The command-line client can also
be integrated into a continuous integration loop or can be used to schedule
maintenance tasks.

Most of the features available in a Web browser opening the analysis result
viewer server on its port is available in the `cmd` tool.

<details>
  <summary><i>$ <b>CodeChecker cmd --help</b> (click to expand)</i></summary>

```
usage: CodeChecker cmd [-h]
                       {runs,history,results,diff,sum,token,del,update,suppress,products,components,login,export,import}
                       ...

The command-line client is used to connect to a running 'CodeChecker server'
(either remote or local) and quickly inspect analysis results, such as runs,
individual defect reports, compare analyses, etc. Please see the invidual
subcommands for further details.

optional arguments:
  -h, --help            show this help message and exit

available actions:
  {runs,history,results,diff,sum,token,del,update,suppress,products,components,login,export,import}
    runs                List the available analysis runs.
    history             Show run history of multiple runs.
    results             List analysis result (finding) summary for a given
                        run.
    diff                Compare two analysis runs and show the difference.
    sum                 Show statistics of checkers.
    token               Access subcommands related to configuring personal
                        access tokens managed by a CodeChecker server.
    del                 Delete analysis runs.
    update              Update an analysis run.
    suppress            Manage and import suppressions of a CodeChecker
                        server.
    products            Access subcommands related to configuring the products
                        managed by a CodeChecker server.
    components          Access subcommands related to configuring the source
                        components managed by a CodeChecker server.
    login               Authenticate into CodeChecker servers that require
                        privileges.
    export              Export comments and review statues for a given run, or
                        if no run is provided, data from all runs is exported
```
</details>

The operations available in `cmd` **always** require a running CodeChecker
viewer server (i.e. a server started by `CodeChecker server`), and the
connection details to access the server. These details either take an URL form
(`--url hostname:port/Productname`) if the command accesses analysis results
in a given product, or a server URL (`--url hostname:port`), if the command
manages the server.

A server started by default settings (`CodeChecker server`, see above)
automatically configure the product `Default` under `localhost:8001/Default`,
thus the `--url` parameter can be omitted.

Most result-giving commands also take an `--output` format parameter. If this
is set to `json`, a more detailed output is given, in JSON format.

If the given output format is not `table` we redirect logger's output to the
`stderr`, so the output of the commands will not be an invalid `json`, `csv`,
etc. because of the log messages. To get a valid json output you can redirect
`stderr` output to `/dev/null` so you can for example send the json output to
another command for further processing:
`CodeChecker cmd sum -n my_run -o json 2>/dev/null | python -m json.tool`.


```
common arguments:
  --host HOST           The address of the CodeChecker viewer server to
                        connect to. (default: localhost)
  --url SERVER_URL      The URL of the server to access, in the format of
                        '[http[s]://]host:port'. (default: localhost:8001)
  --url PRODUCT_URL     The URL of the product which will be accessed by the
                        client, in the format of
                        '[http[s]://]host:port/Endpoint'.
                        (default: localhost:8001/Default)
  -o {plaintext,rows,table,csv,json}, --output {plaintext,rows,table,csv,json}
                        The output format to use in showing the data.
                        (default: plaintext)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.
```

Results can be filtered by using separate filter options of `results`, `diff`,
`sum`, etc. commands.
```
filter arguments:
  --uniqueing {on,off}  The same bug may appear several times if it is found
                        on different execution paths, i.e. through different
                        function calls. By turning on uniqueing a report
                        appears only once even if it is found on several
                        paths.
  --report-hash [REPORT_HASH [REPORT_HASH ...]]
                        Filter results by report hashes.
  --review-status [REVIEW_STATUS [REVIEW_STATUS ...]]
                        Filter results by review statuses.
                        Reports can be assigned a review status of the
                        following values:
                        - Unreviewed: Nobody has seen this report.
                        - Confirmed: This is really a bug.
                        - False positive: This is not a bug.
                        - Intentional: This report is a bug but we don't want
                        to fix it. (default: ['unreviewed', 'confirmed'])
  --detection-status [DETECTION_STATUS [DETECTION_STATUS ...]]
                        Filter results by detection statuses.
                        The detection status is the latest state of a bug
                        report in a run. When a unique report is first
                        detected it will be marked as New. When the report is
                        stored again with the same run name then the detection
                        status changes to one of the following options:
                        - Resolved: when the bug report can't be found after
                        the subsequent storage.
                        - Unresolved: when the bug report is still among the
                        results after the subsequent storage.
                        - Reopened: when a Resolved bug appears again.
                        - Off: The bug was reported by a checker that was
                        switched off during the last analysis which results
                        were stored.
                        - Unavailable: were reported by a checker that does
                        not exists in the analyzer anymore because it was
                        removed or renamed. (default: ['new', 'reopened',
                        'unresolved'])
  --severity [SEVERITY [SEVERITY ...]]
                        Filter results by severities.
  --bug-path-length BUG_PATH_LENGTH
                        Filter results by bug path length. This has the
                        following format:
                        <minimum_bug_path_length>:<maximum_bug_path_length>.
                        Valid values are: "4:10", "4:", ":10"
  --tag [TAG [TAG ...]]
                        Filter results by version tag names.
  --outstanding-reports-date TIMESTAMP, --open-reports-date TIMESTAMP
                        Get results which were detected BEFORE the given date
                        and NOT FIXED BEFORE the given date. The detection
                        date of a report is the storage date when the report
                        was stored to the server for the first time. The
                        format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --file [FILE_PATH [FILE_PATH ...]]
                        Filter results by file path. The file path can contain
                        multiple * quantifiers which matches any number of
                        characters (zero or more). So if you have /a/x.cpp and
                        /a/y.cpp then "/a/*.cpp" selects both.
  --checker-name [CHECKER_NAME [CHECKER_NAME ...]]
                        Filter results by checker names. The checker name can
                        contain multiple * quantifiers which matches any
                        number of characters (zero or more). So for example
                        "*DeadStores" will matches "deadcode.DeadStores"
  --checker-msg [CHECKER_MSG [CHECKER_MSG ...]]
                        Filter results by checker messages.The checker message
                        can contain multiple * quantifiers which matches any
                        number of characters (zero or more).
  --analyzer-name [ANALYZER_NAME [ANALYZER_NAME ...]]
                        Filter results by analyzer names. The analyzer name
                        can contain multiple * quantifiers which match any
                        number of characters (zero or more). So for example
                        "clang*" will match "clangsa" and "clang-tidy".
  --component [COMPONENT [COMPONENT ...]]
                        Filter results by source components. This can be used
                        only if basename or newname is a run name (on the
                        remote server).
  --detected-at TIMESTAMP
                        DEPRECATED. Use the '--detected-after/--detected-
                        before' options to filter results by detection date.
                        Filter results by fix date (fixed after the given
                        date) if the --detection-status filter option is set
                        only to Resolved otherwise it filters the results by
                        detection date (detected after the given date). The
                        format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --fixed-at TIMESTAMP  DEPRECATED. Use the '--fixed-after/--fixed-before'
                        options to filter results by fix date. Filter results
                        by fix date (fixed before the given date) if the
                        --detection-status filter option is set only to
                        Resolved otherwise it filters the results by detection
                        date (detected before the given date). The format of
                        TIMESTAMP is 'year:month:day:hour:minute:second' (the
                        "time" part can be omitted, in which case midnight
                        (00:00:00) is used).
  --detected-before TIMESTAMP
                        Get results which were detected before the given date.
                        The detection date of a report is the storage date
                        when the report was stored to the server for the first
                        time. The format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --detected-after TIMESTAMP
                        Get results which were detected after the given date.
                        The detection date of a report is the storage date
                        when the report was stored to the server for the first
                        time. The format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --fixed-before TIMESTAMP
                        Get results which were fixed before the given date.
                        The format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --fixed-after TIMESTAMP
                        Get results which were fixed after the given date. The
                        format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --anywhere-on-report-path
                        Filter reports where the report path not only ends in
                        the files given by --file or --component, but goes
                        through them. (default: False)
```

#### Source components (`components`)

Source components can be used to group analysis results. A component
is a collection of source files defined by regular expressions on the
path.

<details>
  <summary>
    <i>$ <b>CodeChecker cmd components --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd components [-h] [--url PRODUCT_URL]
                                  [--verbose {info,debug,debug_analyzer}]
                                  {list,add,del} ...

Source components are named collection of directories specified as directory
filter.

optional arguments:
  -h, --help            show this help message and exit

available actions:
  {list,add,del}
    list                List source components available on the serve
    add                 Creates a new source component.
    del                 Delete a source component from the server.
```
</details>


##### New/Edit source component

<details>
  <summary>
    <i>$ <b>CodeChecker cmd components add --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd components add [-h] [--description DESCRIPTION] -i
                                      COMPONENT_FILE [--url PRODUCT_URL]
                                      [--verbose {info,debug,debug_analyzer}]
                                      NAME

Creates a new source component or updates an existing one.

positional arguments:
  NAME                  Unique name of the source component.

optional arguments:
  -h, --help            show this help message and exit
  --description DESCRIPTION
                        A custom textual description to be shown alongside the
                        source component.
  -i COMPONENT_FILE, --import COMPONENT_FILE
                        Path to the source component file which contains
                        multiple file paths. Each file path should start with
                        a '+' or '-' sign.Results will be listed only from
                        paths with a '+' sign. Results will not be listed from
                        paths with a '-' sign. Let's assume there are three
                        directories: test_files, test_data and test_config. In
                        the given example only the results from the test_files
                        and test_data directories will be listed.
                        E.g.:
                        +*/test*/*
                        -*/test_dat*/*
                        Please see the User guide for more information.

```
</details>

###### Format of component file

Source component helps us to filter run results by multiple file paths.

Each line in the source component file should begin with a `+` or a `-`, followed by
a path glob pattern:
 * `+` ONLY results from the matching file paths will be listed
 * `-` results from the matching file paths will not be listed

Example:
```
-/dont/list/results/in/directory/*
-/dont/list/this.file
+/dir/list/in/directory/*
+/dir/list.this.file
```
Results will be listed only from `/dir/list/in/directory/*` and from the
`/dir/list.this.file`.
In this case removing the `-` rules would not change the list of results.

Example 2:
```
+*/test*
+*/test_files/*
+*/test_data/*
-*/test_p*
```
Results will be listed only from the directories which name begin with
`test` except the results form the directories which name begin with `test_p`.

Note: the order of the source component value is not important. E.g.:
```
+/a/b/x.cpp
-/a/b/
```
means the same as
```
-/a/b/
+/a/b/x.cpp
```
`x.cpp` will be included in the run results and all other files under `/a/b/`
path will not be included.

##### List source components
List the name and basic information about source component added to the
server.
```
usage: CodeChecker cmd components list [-h] [--url PRODUCT_URL]
                                       [-o {plaintext,rows,table,csv,json}]
                                       [--verbose {info,debug,debug_analyzer}]

List the name and basic information about source component added to the
server.
```

##### Delete source components

```
usage: CodeChecker cmd components del [-h] [--url PRODUCT_URL]
                                      [--verbose {info,debug,debug_analyzer}]
                                      NAME

Removes the specified source component.

positional arguments:
  NAME                  The source component name which will be removed.
```

#### List runs (`runs`)

<details>
  <summary>
    <i>$ <b>CodeChecker cmd runs --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd runs [-h] [--url PRODUCT_URL]
                            [-o {plaintext,rows,table,csv,json}]
                            [--verbose {info,debug,debug_analyzer}]

List the analysis runs available on the server.

optional arguments:
  -h, --help            show this help message and exit
  -n [RUN_NAME [RUN_NAME ...]], --name [RUN_NAME [RUN_NAME ...]]
                        Names of the analysis runs. If this argument is not
                        supplied it will show all runs. This has the following
                        format: "<run_name_1> <run_name_2> <run_name_3>" where
                        run names can contain multiple * quantifiers which
                        matches any number of characters (zero or more). So if
                        you have run_1_a_name, run_2_b_name, run_2_c_name,
                        run_3_d_name then "run_2* run_3_d_name" shows the last
                        three runs.
  --details             Adds extra details to the run information in JSON
                        format, such as the list of files that are failed to
                        analyze.
  --all-before-run RUN_NAME
                        Get all runs that were stored to the server BEFORE the
                        specified one.
  --all-after-run RUN_NAME
                        Get all runs that were stored to the server AFTER the
                        specified one.
  --all-after-time TIMESTAMP
                        Get all analysis runs that were stored to the server
                        AFTER the given timestamp. The format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --all-before-time TIMESTAMP
                        Get all analysis runs that were stored to the server
                        BEFORE the given timestamp. The format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  --sort {date,duration,codechecker_version,name,unresolved_reports}
                        Sort run data by this column. (default: date)
  --order {asc,desc}    Sort order of the run data. (default: desc)
```
</details>

#### List of run histories (`history`)

With this command you can list out the specific storage events which happened
during storage processes under multiple run names.

<details>
  <summary>
    <i>$ <b>CodeChecker cmd history --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd history [-h] [-n [RUN_NAME [RUN_NAME ...]]]
                               [--url PRODUCT_URL]
                               [-o {plaintext,rows,table,csv,json}]
                               [--verbose {info,debug,debug_analyzer}]

Show run history for some analysis runs.

optional arguments:
  -h, --help            show this help message and exit
  -n [RUN_NAME [RUN_NAME ...]], --name [RUN_NAME [RUN_NAME ...]]
                        Names of the analysis runs to show history for. If
                        this argument is not supplied it will show the history
                        for all runs. This has the following format:
                        "<run_name_1> <run_name_2> <run_name_3>" where run
                        names can contain multiple * quantifiers which matches
                        any number of characters (zero or more). So if you
                        have run_1_a_name, run_2_b_name, run_2_c_name,
                        run_3_d_name then "run_2* run_3_d_name" shows history
                        for the last three runs. Use 'CodeChecker cmd runs' to
                        get the available runs.
```
</details>

#### List analysis results' summary (`results`)

Prints basic information about analysis results, such as location, checker
name, summary.

<details>
  <summary>
    <i>$ <b>CodeChecker cmd results --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd results [-h] [--details] [--uniqueing {on,off}]
                               [--report-hash [REPORT_HASH [REPORT_HASH ...]]]
                               [--review-status [REVIEW_STATUS [REVIEW_STATUS ...]]]
                               [--detection-status [DETECTION_STATUS [DETECTION_STATUS ...]]]
                               [--severity [SEVERITY [SEVERITY ...]]]
                               [--bug-path-length BUG_PATH_LENGTH]
                               [--tag [TAG [TAG ...]]]
                               [--outstanding-reports-date TIMESTAMP]
                               [--file [FILE_PATH [FILE_PATH ...]]]
                               [--checker-name [CHECKER_NAME [CHECKER_NAME ...]]]
                               [--checker-msg [CHECKER_MSG [CHECKER_MSG ...]]]
                               [--analyzer-name [ANALYZER_NAME [ANALYZER_NAME ...]]]
                               [--component [COMPONENT [COMPONENT ...]]]
                               [--detected-at TIMESTAMP]
                               [--fixed-at TIMESTAMP]
                               [--detected-before TIMESTAMP]
                               [--detected-after TIMESTAMP]
                               [--fixed-before TIMESTAMP]
                               [--fixed-after TIMESTAMP] [-s]
                               [--url PRODUCT_URL]
                               [-o {plaintext,rows,table,csv,json}]
                               [--verbose {info,debug,debug_analyzer}]
                               RUN_NAMES [RUN_NAMES ...]

Show the individual analysis reports' summary.

positional arguments:
  RUN_NAMES             Names of the analysis runs to show result summaries
                        of. This has the following format: <run_name_1>
                        <run_name_2> <run_name_3> where run names can contain
                        * quantifiers which matches any number of characters
                        (zero or more). So if you have run_1_a_name,
                        run_2_b_name, run_2_c_name, run_3_d_name then "run_2*
                        run_3_d_name" selects the last three runs. Use
                        'CodeChecker cmd runs' to get the available runs.

optional arguments:
  -h, --help            show this help message and exit
  --details             Get report details for reports such as bug path
                        events, bug report points etc.
```
</details>

##### Example
```
#Get analysis results for a run:
CodeChecker cmd results my_run

# Get analysis results for multiple runs:
CodeChecker cmd results my_run1 my_run2

# Get analysis results by using regex:
CodeChecker cmd results "my_run*"

# Get analysis results for a run and filter the analysis results:
CodeChecker cmd results my_run --severity critical high medium \
    --file "/home/username/my_project/*"

# Get detailed analysis results for a run in JSON format.
CodeChecker cmd results -o json --details my_run
```

#### Show differences between two runs (`diff`)

Please see [Comparing analysis results (Diff)](diff.md) for details.

#### Show summarised count of results (`sum`)
<details>
  <summary>
    <i>$ <b>CodeChecker cmd sum --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd sum [-h] (-n RUN_NAME [RUN_NAME ...] | -a)
                           [--uniqueing {on,off}]
                           [--report-hash [REPORT_HASH [REPORT_HASH ...]]]
                           [--review-status [REVIEW_STATUS [REVIEW_STATUS ...]]]
                           [--detection-status [DETECTION_STATUS [DETECTION_STATUS ...]]]
                           [--severity [SEVERITY [SEVERITY ...]]]
                           [--bug-path-length BUG_PATH_LENGTH]
                           [--tag [TAG [TAG ...]]]
                           [--outstanding-reports-date TIMESTAMP]
                           [--file [FILE_PATH [FILE_PATH ...]]]
                           [--checker-name [CHECKER_NAME [CHECKER_NAME ...]]]
                           [--checker-msg [CHECKER_MSG [CHECKER_MSG ...]]]
                           [--analyzer-name [ANALYZER_NAME [ANALYZER_NAME ...]]]
                           [--component [COMPONENT [COMPONENT ...]]]
                           [--detected-at TIMESTAMP] [--fixed-at TIMESTAMP]
                           [--detected-before TIMESTAMP]
                           [--detected-after TIMESTAMP]
                           [--fixed-before TIMESTAMP]
                           [--fixed-after TIMESTAMP] [-s]
                           [--url PRODUCT_URL]
                           [-o {plaintext,rows,table,csv,json}]
                           [--verbose {info,debug,debug_analyzer}]

Show checker statistics for some analysis runs.

optional arguments:
  -h, --help            show this help message and exit
  -n RUN_NAME [RUN_NAME ...], --name RUN_NAME [RUN_NAME ...]
                        Names of the analysis runs to show result count
                        breakdown for. This has the following format:
                        <run_name_1>:<run_name_2>:<run_name_3> where run names
                        can contain multiple * quantifiers which matches any
                        number of characters (zero or more). So if you have
                        run_1_a_name, run_2_b_name, run_2_c_name, run_3_d_name
                        then "run_2*:run_3_d_name" selects the last three
                        runs. Use 'CodeChecker cmd runs' to get the available
                        runs.
  -a, --all             Show breakdown for all analysis runs.
```
</details>

##### Summary Example
```sh
# Get statistics for a run:
CodeChecker cmd sum -n my_run

# Get statistics for all runs filtered by multiple checker names:
CodeChecker cmd sum --all --checker-name "core.*" "deadcode.*"

# Get statistics for all runs and only for severity 'high':
CodeChecker cmd sum --all --severity "high"
```

#### Remove analysis runs (`del`)
<details>
  <summary>
    <i>$ <b>CodeChecker cmd del --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd del [-h]
                           (-n RUN_NAME [RUN_NAME ...] |
                            --all-before-run RUN_NAME |
                            --all-after-run RUN_NAME |
                            --all-after-time TIMESTAMP |
                            --all-before-time TIMESTAMP)
                           [--url PRODUCT_URL]
                           [--verbose {info,debug,debug_analyzer}]

Remove analysis runs from the server based on some criteria.

!!! WARNING !!! When a run is deleted, ALL associated information (reports,
files, run histories) is PERMANENTLY LOST! Please be careful with this command
because it can not be undone.

NOTE! You can't remove a snapshot of run (a run history), you can remove only
full runs.

optional arguments:
  -h, --help            show this help message and exit
  -n RUN_NAME [RUN_NAME ...], --name RUN_NAME [RUN_NAME ...]
                        Full name of the analysis run or runs to delete.
  --all-before-run RUN_NAME
                        Delete all runs that were stored to the server BEFORE
                        the specified one.
  --all-after-run RUN_NAME
                        Delete all runs that were stored to the server AFTER
                        the specified one.
  --all-after-time TIMESTAMP
                        Delete all analysis runs that were stored to the
                        server AFTER the given timestamp. The format of
                        TIMESTAMP is 'year:month:day:hour:minute:second' (the
                        "time" part can be omitted, in which case midnight
                        (00:00:00) is used).
  --all-before-time TIMESTAMP
                        Delete all analysis runs that were stored to the
                        server BEFORE the given timestamp. The format of
                        TIMESTAMP is 'year:month:day:hour:minute:second' (the
                        "time" part can be omitted, in which case midnight
                        (00:00:00) is used).
```
</details>

#### Update an analysis run (`update`)
<details>
  <summary>
    <i>$ <b>CodeChecker cmd update --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd update [-h] -n NEW_RUN_NAME [--url PRODUCT_URL]
                              [--verbose {info,debug,debug_analyzer}]
                              run_name

Update the name of an analysis run.

positional arguments:
  run_name              Full name of the analysis run to update.

optional arguments:
  -h, --help            show this help message and exit
  -n NEW_RUN_NAME, --name NEW_RUN_NAME
                        Name name of the analysis run.
```
</details>

#### Import suppressions (`suppress`)
If cannot use `in-line` code suppressions, such as `//codechecker_suppress`,
but you would like to keep your suppressions under version control, you
can use suppress files, to indicate which report is **false positive**.


<details>
  <summary>
    <i>$ <b>CodeChecker cmd suppress --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd suppress [-h] [-f] -i SUPPRESS_FILE [--url PRODUCT_URL]
                                [--verbose {info,debug,debug_analyzer}]
                                RUN_NAME

Imports suppressions from a suppress file to a CodeChecker server.

positional arguments:
  RUN_NAME              Name of the analysis run to suppress or unsuppress a
                        report in.

optional arguments:
  -h, --help            show this help message and exit
  -f, --force           Enable suppression of already suppressed reports.
  -i SUPPRESS_FILE, --import SUPPRESS_FILE
                        Import suppression from the suppress file into the
                        database.
```
</details>

##### Import suppressions from a suppress file

Suppressions are imported as individual report suppressions
(as opposed to suppression rules).
So only those reports will be suppressed that are part of the given
RUN_NAME run.

```
  -i SUPPRESS_FILE, --import SUPPRESS_FILE
                        Import suppression from the suppress file into the
                        database.
```

`--import` **appends** the suppressions found in the given suppress file to
the database on the server.

The suppression file has the following format
```
report_hash||source_file_name||suppress_comment||type_of_suppression

```

* `report_hash` is the hash identifier of the report to be suppressed
* `source_file_name` is the name of the source file wher the report is located
* `suppress_comment` why you think the issue should be suppressed
* `type_of_suppression` one of the following `false_positive`, `intentional`,
  `confirmed`

An example suppress file:

```
1a7ddce6d69b031310dd7ad2ff330b53||suppress.cpp||foo2 simple||false_positive
45a2fef6845f54eaf070ad03d19c7981||suppress.cpp||foo3 simple||intentional
9fb26da7f3224ec0c63cfe3617c8a14e||suppress.cpp||foo4 simple||confirmed
```

#### Manage product configuration of a server (`products`)

Please see [Product management](products.md) for details.

#### Query authorization settings (`permissions`)
You can use this command to get access control information from a running
CodeChecker server. This will contain information which user or group has
global permissions or permissions only for specific products.

The output format of this command is the following:
```json
{
  "version": 1,
  "global_permissions": {
    "user_permissions": {
      "<user-name-1>": ["<permission-1>"]
    },
    "group_permissions": {
    }
  },
  "product_permissions": {
    "<product-name>": {
      "user_permissions": {
        "<user-name-2>": ["<permission-2>", "<permission-3>"]
      },
      "group_permissions": {
        "<group-name-1>": ["<permission-3>"]
      }
    }
  }
}
```

<details>
  <summary>
    <i>$ <b>CodeChecker cmd permissions --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd permissions [-h] [-o {json}] [--url SERVER_URL]
                                   [--verbose {info,debug_analyzer,debug}]

Get access control information from a CodeChecker server. PERMISSION_VIEW
access right is required to run this command.

optional arguments:
  -h, --help            show this help message and exit
  -o {json}, --output {json}
                        The output format to use in showing the data.
                        (default: json)

common arguments:
  --url SERVER_URL      The URL of the server to access, in the format of
                        '[http[s]://]host:port'. (default: localhost:8001)
  --verbose {info,debug_analyzer,debug}
                        Set verbosity level.
```
</details>

#### Authenticate to the server (`login`)
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

If a server [requires privileged access](authentication.md), you must
log in before you can access the data on the particular server. Once
authenticated, your session is available for some time and `CodeChecker cmd`
can be used normally.

The password can be saved on the disk. If such "preconfigured" password is
not found, the user will be asked, in the command-line, to provide credentials.

#### Server-side task management (`serverside-tasks`)
<details>
  <summary>
    <i>$ <b>CodeChecker cmd serverside-tasks --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker cmd serverside-tasks [-h] [-t [TOKEN [TOKEN ...]]]
                                        [--await] [--kill]
                                        [--output {plaintext,table,json}]
                                        [--machine-id [MACHINE_ID [MACHINE_ID ...]]]
                                        [--type [TYPE [TYPE ...]]]
                                        [--status [{allocated,enqueued,running,completed,failed,cancelled,dropped} [{allocated,enqueued,running,completed,failed,cancelled,dropped} ...]]]
                                        [--username [USERNAME [USERNAME ...]]
                                        | --no-username]
                                        [--product [PRODUCT [PRODUCT ...]] |
                                        --no-product]
                                        [--enqueued-before TIMESTAMP]
                                        [--enqueued-after TIMESTAMP]
                                        [--started-before TIMESTAMP]
                                        [--started-after TIMESTAMP]
                                        [--finished-before TIMESTAMP]
                                        [--finished-after TIMESTAMP]
                                        [--last-seen-before TIMESTAMP]
                                        [--last-seen-after TIMESTAMP]
                                        [--only-cancelled | --no-cancelled]
                                        [--only-consumed | --no-consumed]
                                        [--url SERVER_URL]
                                        [--verbose {info,debug_analyzer,debug}]

Query the status of and otherwise filter information for server-side
background tasks executing on a CodeChecker server. In addition, for server
administartors, allows requesting tasks to cancel execution.

Normally, the querying of a task's status is available only to the following
users:
  - The user who caused the creation of the task.
  - For tasks that are associated with a specific product, the PRODUCT_ADMIN
    users of that product.
  - Accounts with SUPERUSER rights (server administrators).

optional arguments:
  -h, --help            show this help message and exit
  -t [TOKEN [TOKEN ...]], --token [TOKEN [TOKEN ...]]
                        The identifying token(s) of the task(s) to query. Each
                        task is associated with a unique token. (default:
                        None)
  --await               Instead of querying the status and reporting that,
                        followed by an exit, block execution of the
                        'CodeChecker cmd serverside-tasks' program until the
                        queried task(s) terminate(s). Makes the CLI's return
                        code '0' if the task(s) completed successfully, and
                        non-zero otherwise. If '--kill' is also specified, the
                        CLI will await the shutdown of the task(s), but will
                        return '0' if the task(s) were successfully killed as
                        well. (default: False)
  --kill                Request the co-operative and graceful termination of
                        the tasks matching the filter(s) specified. '--kill'
                        is only available to SUPERUSERs! Note, that this
                        action only submits a *REQUEST* of termination to the
                        server, and tasks are free to not support in-progress
                        kills. Even for tasks that support getting killed, due
                        to its graceful nature, it might take a considerable
                        time for the killing to conclude. Killing a task that
                        has not started RUNNING yet results in it
                        automatically terminating before it would start.
                        (default: False)

output arguments:
  --output {plaintext,table,json}
                        The format of the output to use when showing the
                        result of the request. (default: plaintext)

task list filter arguments:
  These options can be used to obtain and filter the list of tasks
  associated with the 'CodeChecker server' specified by '--url', based on the
  various information columns stored for tasks.

  '--token' is usable with the following filters as well.

  Filters with a variable number of options (e.g., '--machine-id A B') will be
  in a Boolean OR relation with each other (meaning: machine ID is either "A"
  or "B").
  Specifying multiple filters (e.g., '--machine-id A B --username John') will
  be considered in a Boolean AND relation (meaning: [machine ID is either "A" or
  "B"] and [the task was created by "John"]).

  Listing is only available for the following, privileged users:
    - For tasks that are associated with a specific product, the PRODUCT_ADMINs
     of that product.
    - Server administrators (SUPERUSERs).

  Unprivileged users MUST use only the task's token to query information about
  the task.


  --machine-id [MACHINE_ID [MACHINE_ID ...]]
                        The IDs of the server instance executing the tasks.
                        This is an internal identifier set by server
                        administrators via the 'CodeChecker server' command.
                        (default: None)
  --type [TYPE [TYPE ...]]
                        The descriptive, but still machine-readable "type" of
                        the tasks to filter for. (default: None)
  --status [{allocated,enqueued,running,completed,failed,cancelled,dropped} [{allocated,enqueued,running,completed,failed,cancelled,dropped} ...]]
                        The task's execution status(es) in the pipeline.
                        (default: None)
  --username [USERNAME [USERNAME ...]]
                        The user(s) who executed the action that caused the
                        tasks' creation. (default: None)
  --no-username         Filter for tasks without a responsible user that
                        created them. (default: False)
  --product [PRODUCT [PRODUCT ...]]
                        Filter for tasks that execute in the context of
                        products specified by the given ENDPOINTs. This query
                        is only available if you are a PRODUCT_ADMIN of the
                        specified product(s). (default: None)
  --no-product          Filter for server-wide tasks (not associated with any
                        products). This query is only available to SUPERUSERs.
                        (default: False)
  --enqueued-before TIMESTAMP
                        Filter for tasks that were created BEFORE (or on) the
                        specified TIMESTAMP, which is given in the format of
                        'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --enqueued-after TIMESTAMP
                        Filter for tasks that were created AFTER (or on) the
                        specified TIMESTAMP, which is given in the format of
                        'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --started-before TIMESTAMP
                        Filter for tasks that were started execution BEFORE
                        (or on) the specified TIMESTAMP, which is given in the
                        format of 'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --started-after TIMESTAMP
                        Filter for tasks that were started execution AFTER (or
                        on) the specified TIMESTAMP, which is given in the
                        format of 'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --finished-before TIMESTAMP
                        Filter for tasks that concluded execution BEFORE (or
                        on) the specified TIMESTAMP, which is given in the
                        format of 'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --finished-after TIMESTAMP
                        Filter for tasks that concluded execution execution
                        AFTER (or on) the specified TIMESTAMP, which is given
                        in the format of 'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --last-seen-before TIMESTAMP
                        Filter for tasks that reported actual forward progress
                        in its execution ("heartbeat") BEFORE (or on) the
                        specified TIMESTAMP, which is given in the format of
                        'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --last-seen-after TIMESTAMP
                        Filter for tasks that reported actual forward progress
                        in its execution ("heartbeat") AFTER (or on) the
                        specified TIMESTAMP, which is given in the format of
                        'year:month:day' or
                        'year:month:day:hour:minute:second'. If the "time"
                        part (':hour:minute:second') is not given, 00:00:00
                        (midnight) is assumed instead. Timestamps for tasks
                        are always understood as Coordinated Universal Time
                        (UTC). (default: None)
  --only-cancelled      Show only tasks that received a cancel request from a
                        SUPERUSER (see '--kill'). (default: False)
  --no-cancelled        Show only tasks that had not received a cancel request
                        from a SUPERUSER (see '--kill'). (default: False)
  --only-consumed       Show only tasks that concluded their execution and the
                        responsible user (see '--username') "downloaded" this
                        fact. (default: False)
  --no-consumed         Show only tasks that concluded their execution but the
                        responsible user (see '--username') did not "check" on
                        the task. (default: False)

common arguments:
  --url SERVER_URL      The URL of the server to access, in the format of
                        '[http[s]://]host:port'. (default: localhost:8001)
  --verbose {info,debug_analyzer,debug}
                        Set verbosity level.

The return code of 'CodeChecker cmd serverside-tasks' is almost always '0',
unless there is an error.
If **EXACTLY** one '--token' is specified in the arguments without the use of
'--await' or '--kill', the return code is based on the current status of the
task, as identified by the token:
  -  0: The task completed successfully.
  -  1: (Reserved for operational errors.)
  -  2: (Reserved for command-line errors.)
  -  4: The task failed to complete due to an error during execution.
  -  8: The task is still running...
  - 16: The task was cancelled by the administrators, or the server was shut
        down.
```
</details>

The `serverside-tasks` subcommand allows users and administrators to query the status of (and for administrators, request the cancellation) of **server-side background tasks**.
These background tasks are created by a limited set of user actions, where the user's client not waiting for the completion of the task can be beneficial.
A task is always identified by its **token**, which is a random generated value.
This token is presented to the user when appropriate.

##### Querying the status of a single job

The primary purpose of `CodeChecker cmd serverside-tasks` is to query the status of a running task, with the `--token TOKEN` flag, e.g., `CodeChecker cmd serverside-tasks --token ABCDEF`.
This will return the task's details:

```
Task 'ABCDEF':
    - Type:         TaskService::DummyTask
    - Summary:      Dummy task for testing purposes
    - Status:       CANCELLED
    - Enqueued at:  2024-08-19 15:55:34
    - Started at:   2024-08-19 15:55:34
    - Last seen:    2024-08-19 15:55:35
    - Completed at: 2024-08-19 15:55:35

Comments on task '8b62497c7d1b7e3945445f5b9c3951d97ae07e58f97cad60a0187221e7d1e2ba':
...
```

If `--await` is also specified, the execution of `CodeChecker cmd serverside-task` blocks the caller prompt or script until the task terminates on the server.
This is useful in situations where the side effect of a task is needed to be ready before the script may process further instructions.

A task can have the following statuses:

  * **Allocated**: The task's token was minted, but the complete input to the task has not yet fully processed.
  * **Enqueued**: The task is ready for execution, and the system is waiting for free resources to begin running the implementation.
  * **Running**: The task is actively executing.
  * **Completed**: The task successfully finished executing. (The side effects of the operations are available at this point.)
  * **Failed**: The task's execution was started, but failed for some reason. This could be an error detected in the input, a database issue, or any other _Exception_. The "Comments" field of the task, when queried, will likely contain the details of the error.
  * **Cancelled**: The task was cancelled by an administrator ([see later](#requesting-the-termination-of-a-task-only-for-SUPERUSERs)) and the task shut down to this request.
  * **Dropped**: The task's execution was interrupted due to an external reason (system crash, service shutdown).

##### Querying multiple tasks via filters

For product and server administrators (`PRODUCT_ADMIN` and `SUPERUSER` rights), the `serverside-tasks` subcommand exposes various filter options, which can be used to create even a combination of criteria tasks must match to be returned.
Please refer to the `--help` of the subcommand for the exact list of filters available.
In this mode, the statuses of the tasks are printed in a concise table.

```sh
$ CodeChecker cmd serverside-tasks --enqueued-after 2024:08:19 --status cancelled

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Token                                                            | Machine            | Type                   | Summary                         | Status    | Product | User | Enqueued            | Started             | Last seen           | Completed           | Cancelled?
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
8b62497c7d1b7e3945445f5b9c3951d97ae07e58f97cad60a0187221e7d1e2ba | xxxxxxxxxxxxx:8001 | TaskService::DummyTask | Dummy task for testing purposes | CANCELLED |         |      | 2024-08-19 15:55:34 | 2024-08-19 15:55:34 | 2024-08-19 15:55:35 | 2024-08-19 15:55:35 | Yes
6fa0097a9bd1799572c7ccd2afc0272684ed036c11145da7eaf40cc8a07c7241 | xxxxxxxxxxxxx:8001 | TaskService::DummyTask | Dummy task for testing purposes | CANCELLED |         |      | 2024-08-19 15:55:53 | 2024-08-19 15:55:53 | 2024-08-19 15:55:53 | 2024-08-19 15:55:53 | Yes
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

##### Requesting the termination of a task (only for `SUPERUSER`s)

Tasks matching the query filters can be requested for termination ("killed") by specifying `--kill` in addition to the filters.
This will send a request to the server to shut the tasks down.

**Note**, that this shutdown is not deterministic and is not immediate.
Due to technical reasons, it is up for the task's implementation to find the appropriate position to honour the shutdown request.
Depending on the task's semantics, the input, or simply circumstance, a task may completely ignore the shutdown request and decide to nevertheless complete.


### Exporting source code suppression to suppress file

```
  --export-source-suppress
                        Write suppress data from the suppression annotations
                        found in the source files that were analyzed earlier
                        that created the results.
```

```sh
CodeChecker parse ./my_results --suppress generated.suppress --export-source-suppress
```

#### Export comments and review statuses (`export`)

```sh
usage: CodeChecker cmd export [-h] [-n RUN_NAME [RUN_NAME ...]]
                              [--url PRODUCT_URL]
                              [--verbose {info,debug_analyzer,debug}]

Export data (comments, review statuses) from a running CodeChecker server into
a json format

optional arguments:
  -h, --help            show this help message and exit
  -n RUN_NAME [RUN_NAME ...], --name RUN_NAME [RUN_NAME ...]
                        Name of the analysis run.
```
 For redirecting the output to a json file, use the command:
 ```sh
 CodeChecker cmd export -n <run_name_1> <run_name_2> ... 2>/dev/null | python -m json.tool > <file_name>.json
 ```
 In the above command multiple runs can be pass as, the `...` indicate any additional runs, if needed to be provided


#### Import comments and review statuses into Codechecker (`import`)
```sh
usage: CodeChecker cmd import [-h] -i JSON_FILE [--url PRODUCT_URL]
                              [--verbose {info,debug_analyzer,debug}]

Import the results into CodeChecker server

optional arguments:
  -h, --help            show this help message and exit
  -i JSON_FILE, --import JSON_FILE
                        Import findings from the json file into the database.
```

### `version`
#### JSON format
The JSON output format looks like this:
```json
{
  "analyzer": {
    "base_package_version": "6.19.0",
    "package_build_date": "2021-12-15T16:07",
    "git_commit": "ed16b5d58f75002b465ea0944be0abf071f0b958",
    "git_tag": "6.19"
  },
  "web": {
    "base_package_version": "6.19.0",
    "package_build_date": "2021-12-15T16:07",
    "git_commit": "ed16b5d58f75002b465ea0944be0abf071f0b958",
    "git_tag": "6.19",
    "server_api_version": [
      "6.47"
    ],
    "client_api_version": "6.47"
  }
}
```

In JSON output we have two main sections:
- `analyzer` (null | object): Analyzer version information if it's available.
  - `base_package_version` (string): Base package version in
  `<major>.<minor>.<revision>` format.
  - `package_build_date` (string): Date time when the package was built.
  - `git_commit` (null | string): Git commit ID (hash).
  - `git_tag` (null | string): Git tag information.
- `web` (null | object): Web version information if it's available.
  - `base_package_version` (string): Base package version in
  `<major>.<minor>.<revision>` format.
  - `package_build_date` (string): Date time when the package was built.
  - `git_commit` (null | string): Git commit ID (hash).
  - `git_tag` (null | string): Git tag information.
  - `server_api_version` (list[string]): Server supported Thrift API version.
  - `client_api_version` (str): Client Thrift API version.


## Log Levels

To change the log levels check out the [logging](../logging.md) documentation.
