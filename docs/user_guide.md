# CodeChecker

First of all, you have to setup the environment for CodeChecker.
Codechecker server uses SQLite database (by default) to store the results which is also packed into the package.

The next step is to start the CodeChecker main script.
The main script can be started with different options.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker [-h]

                   {check,quickcheck,log,checkers,server,cmd,debug,plist,version}
                   ...

Run the CodeChecker source analyzer framework.
See the subcommands for specific features.

positional arguments:
  {check,quickcheck,log,checkers,server,cmd,debug,plist,version}
                        commands
    check               Run the supported source code analyzers on a project.
    quickcheck          Run CodeChecker for aproject without database.
    log                 Runs the given build command. During the build the
                        compilation commands are collected and stored into a
                        compilation command json file (no analysis is done
                        during the build).
    checkers            List the available checkers for the supported
                        analyzers and show their default status (+ for being
                        enabled, - for being disabled by default).
    server              Start the codechecker web server.
    cmd                 Command line client
    debug               Generate gdb debug dump files for all the failed
                        compilation commands in the last analyzer run.
                        Requires a database with the failed compilation
                        commands.
    plist               Parse plist files in the given directory.
    version             Print package version information.

optional arguments:
  -h, --help            show this help message and exit

Example usage:
--------------
Analyzing a project with default settings:
CodeChecker check -w ~/workspace -b "cd ~/myproject && make" -n myproject

Start the viewer to see the results:
CodeChecker server -w ~/workspace

~~~~~~~~~~~~~~~~~~~~~


## Default configuration

Used ports:
* `5432` - PostgreSQL
* `8001` - CodeChecker result viewer

# Easy analysis wrappers

CodeChecker provides, along with the more fine-tuneable commands, some easy
out-of-the-box invocations to ensure the most user-friendly operation. These
two modes are called **quickcheck** and **check**.

## Quickcheck

It is possible to easily analyse the project for defects without keeping the
temporary analysis files and without using any database to store the reports
in, but instead printing the found issues to the standard output.

To analyse your project by doing a build and reporting every found issue in the
built files, execute

~~~~~~~~~~~~~~~~~~~~~
CodeChecker quickcheck --build "make"
~~~~~~~~~~~~~~~~~~~~~

Please make sure your build command actually compiles (builds) the source
files you intend to analyse, as CodeChecker only analyzes files that had been
used by the build system.

If you have an already existing JSON Compilation Commands file, you can also
supply it to `quickcheck`:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker quickcheck --logfile ./my-build.json
~~~~~~~~~~~~~~~~~~~~~

By default, only the report's main messages are printed. To print the
individual steps the analysers took in discovering the issue, specify
`--steps`.

`quickcheck` is a wrapper over the following calls:

 * If `--build` is specified, the build is executed as if `CodeChecker log`
   were invoked.
 * The resulting logfile, or a `--logfile` specified is used for `CodeChecker
   analyze`
 * The analysis results are feeded for `CodeChecker parse`.

After the results has been printed to the standard output, the temporary files
used for the analysis are cleaned up.

Please see the individual help for `log`, `analyze` and `parse` (below in this
_User guide_) for information about the arguments of `quickcheck`.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker quickcheck [-h] [-q] (-b COMMAND | -l LOGFILE)
                              [-j JOBS] [-i SKIPFILE]
                              [--analyzers ANALYZER [ANALYZER ...]]
                              [--add-compiler-defaults]
                              [--saargs CLANGSA_ARGS_CFG_FILE]
                              [--tidyargs TIDY_ARGS_CFG_FILE]
                              [-e checker/checker-group]
                              [-d checker/checker-group] [-u SUPPRESS] [-s]
                              [--verbose {info,debug,debug_analyzer}]

Run analysis for a project with printing results immediately on the standard
output. Quickcheck only needs a build command or an already existing logfile
and performs every step of doing the analysis in batch.

optional arguments:
  -h, --help            show this help message and exit
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)

log arguments:

  -q, --quiet-build
  -b COMMAND, --build COMMAND
  -l LOGFILE, --logfile LOGFILE

analyzer arguments:

  -j JOBS, --jobs JOBS
  -i SKIPFILE, --skip SKIPFILE
  --analyzers ANALYZER [ANALYZER ...]
  --add-compiler-defaults
  --saargs CLANGSA_ARGS_CFG_FILE
  --tidyargs TIDY_ARGS_CFG_FILE

checker configuration:

  -e checker/checker-group, --enable checker/checker-group
  -d checker/checker-group, --disable checker/checker-group

output arguments:

  -u SUPPRESS, --suppress SUPPRESS
  -s, --steps, --print-steps
~~~~~~~~~~~~~~~~~~~~~

# Available CodeChecker commands

## 1. `log` mode

The first step in performing an analysis on your project is to record
information about the files in your project for the analyzers. This is done by
recording a build of your project, which is done by the command `CodeChecker
log`.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker log [-h] -o LOGFILE -b COMMAND
                       [--verbose {info,debug,debug_analyzer}]

Runs the given build command and records the executed compilation steps. These
steps are written to the output file in a JSON format. Available build logger
tool that will be used is '...'.

optional arguments:
  -h, --help            show this help message and exit
  -o LOGFILE, --output LOGFILE
                        Path of the file to write the collected compilation
                        commands to. If the file already exists, it will be
                        overwritten.
  -b COMMAND, --build COMMAND
                        The build command to execute. Build commands can be
                        simple calls to 'g++' or 'clang++' or 'make', but a
                        more complex command, or the call of a custom script
                        file is also supported.
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

Please note, that only the files that are used in the given `--build` argument
will be recorded. To analyze your whole project, make sure your build tree has
been cleaned before `log`ging.

You can change the compilers that should be logged.
Set `CC_LOGGER_GCC_LIKE` environment variable to a colon separated list.
For example (default):

~~~~~~~~~~~~~~~~~~~~~
export CC_LOGGER_GCC_LIKE="gcc:g++:clang"
~~~~~~~~~~~~~~~~~~~~~

Example:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker log -o ../codechecker_myProject_build.log -b "make -j2"
~~~~~~~~~~~~~~~~~~~~~

## 2. check mode:

### Basic Usage

Database and connections will be automatically configured.
The main script starts and setups everything what is required for analyzing a project (database server, tables ...).

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -w codechecker_workspace -n myTestProject -b "make"
~~~~~~~~~~~~~~~~~~~~~

Static analysis can be started also by using an already generated buildlog (see log mode).
If log is not available the analyzer will automatically create it.
An already created CMake json compilation database can be used as well.

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -w ~/codechecker_wp -n myProject -l ~/codechecker_wp/build_log.json
~~~~~~~~~~~~~~~~~~~~~

### Advanced Usage

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker check [-h] [-w WORKSPACE] -n NAME (-b COMMAND | -l LOGFILE)
                         [-j JOBS] [-u SUPPRESS] [-c [DEPRECATED]]
                         [--update [DEPRECATED]] [--force] [-s SKIPFILE]
                         [--quiet-build] [--add-compiler-defaults] [-e ENABLE]
                         [-d DISABLE] [--keep-tmp]
                         [--analyzers ANALYZERS [ANALYZERS ...]]
                         [--saargs CLANGSA_ARGS_CFG_FILE]
                         [--tidyargs TIDY_ARGS_CFG_FILE]
                         [--sqlite [DEPRECATED]] [--postgresql]
                         [--dbport DBPORT] [--dbaddress DBADDRESS]
                         [--dbname DBNAME] [--dbusername DBUSERNAME]
                         [--verbose {info,debug,debug_analyzer}]

optional arguments:
  -h, --help            show this help message and exit
  -w WORKSPACE, --workspace WORKSPACE
                        Directory where the CodeChecker can store analysis
                        related data. (default: /home/<user_home>/.codechecker)
  -n NAME, --name NAME  Name of the analysis.
  -b COMMAND, --build COMMAND
                        Build command which is used to build the project.
  -l LOGFILE, --log LOGFILE
                        Path to the log file which is created during the
                        build. If there is an already generated log file with
                        the compilation commands generated by 'CodeChecker
                        log' or 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS'
                        CodeChecker check can use it for the analysis in that
                        case running the original build will be left out from
                        the analysis process (no log is needed).
  -j JOBS, --jobs JOBS  Number of jobs. Start multiple processes for faster
                        analysis. (default: 1)
  -u SUPPRESS, --suppress SUPPRESS
                        Path to suppress file. Suppress file can be used to
                        suppress analysis results during the analysis. It is
                        based on the bug identifier generated by the compiler
                        which is experimental. Do not depend too much on this
                        file because identifier or file format can be changed.
                        For other in source suppress features see the user
                        guide.
  -c [DEPRECATED], --clean [DEPRECATED]
                        DEPRECATED argument! (default: None)
  --update [DEPRECATED]
                        DEPRECATED argument! (default: None)
  --force               Delete analysis results form the database if a run
                        with the given name already exists. (default: False)
  -s SKIPFILE, --skip SKIPFILE
                        Path to skip file.
  --quiet-build         Do not print out the output of the original build.
                        (default: False)
  --add-compiler-defaults
                        Fetch built in compiler include paths and defines and
                        pass them to Clang. This is useful when you do cross-
                        compilation. (default: False)
  -e ENABLE, --enable ENABLE
                        Enable checker.
  -d DISABLE, --disable DISABLE
                        Disable checker.
  --keep-tmp            Keep temporary report files generated during the
                        analysis. (default: False)
  --analyzers ANALYZERS [ANALYZERS ...]
                        Select which analyzer should be enabled. Currently
                        supported analyzers are: clangsa clang-tidy e.g. '--
                        analyzers clangsa clang-tidy' (default: ['clangsa',
                        'clang-tidy'])
  --saargs CLANGSA_ARGS_CFG_FILE
                        File with arguments which will be forwarded directly
                        to the Clang static analyzer without modification.
  --tidyargs TIDY_ARGS_CFG_FILE
                        File with arguments which will be forwarded directly
                        to the Clang tidy analyzer without modification.
  --sqlite [DEPRECATED]
                        DEPRECATED argument! (default: None)
  --postgresql          Use PostgreSQL database. (default: False)
  --dbport DBPORT       Postgres server port. (default: 5432)
  --dbaddress DBADDRESS
                        Postgres database server address. (default: localhost)
  --dbname DBNAME       Name of the database. (default: codechecker)
  --dbusername DBUSERNAME
                        Database user name. (default: codechecker)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~


### Using SQLite for database:

CodeChecker can also use SQLite for storing the results. In this case the
SQLite database will be created in the workspace directory.

In order to use PostgreSQL instead of SQLite, use the `--postgresql` command
line argument for `CodeChecker server` and `CodeChecker check`
commands. If `--postgresql` is not given then SQLite is used by default in
which case `--dbport`, `--dbaddress`, `--dbname`, and
`--dbusername` command line arguments are ignored.

#### Note:
Schema migration is not supported with SQLite. This means if you upgrade your
CodeChecker to a newer version, you might need to re-check your project.

### Suppression in the source:

Suppress comments can be used in the source to suppress specific or all checker results found in a source line.
Suppress comment should be above the line where the bug was found no empty lines are allowed between the line with the bug and the suppress comment.
Only comment lines staring with "//" are supported

Supported comment formats:

~~~~~~~~~~~~~~~~~~~~~
void test() {
  int x;
  // codechecker_suppress [deadcode.DeadStores] suppress deadcode
  x = 1; // warn
}
~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~
void test() {
  int x;
  // codechecker_suppress [all] suppress all checker results
  x = 1; // warn
}
~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~
void test() {
  int x;

  // codechecker_suppress [all] suppress all
  // checker resuls
  // with a long
  // comment
  x = 1; // warn
}
~~~~~~~~~~~~~~~~~~~~~

### Various deployment possibilities

The CodeChecker server can be started separately when desired.
In that case multiple clients can use the same database to store new results or view old ones.


#### Codechecker server and database on the same machine

Codechecker server and the database are running on the same machine but the database server is started manually.
In this case the database handler and the database can be started manually by running the server command.
The workspace needs to be provided for both the server and the check commands.

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server -w ~/codechecker_wp --dbname myProjectdb --dbport 5432 --dbaddress localhost --view-port 8001
~~~~~~~~~~~~~~~~~~~~~

The checking process can be started separately on the same machine

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check  -w ~/codechecker_wp -n myProject -b "make -j 4" --dbname myProjectdb --dbaddress localhost --dbport 5432
~~~~~~~~~~~~~~~~~~~~~

or on a different machine

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check  -w ~/codechecker_wp -n myProject -b "make -j 4" --dbname myProjectdb --dbaddress 192.168.1.1 --dbport 5432
~~~~~~~~~~~~~~~~~~~~~


#### Codechecker server and database are on different machines

It is possible that the CodeChecker server and the PostgreSQL database that contains the analysis results are on different machines. To setup PostgreSQL see later section.

In this case the CodeChecker server can be started using the following command:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server --dbname myProjectdb --dbport 5432 --dbaddress 192.168.1.2 --view-port 8001
~~~~~~~~~~~~~~~~~~~~~

Start CodeChecker server locally which connects to a remote database (which is started separately). Workspace is not required in this case.


Start the checking as explained previously.

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -w ~/codechecker_wp -n myProject -b "make -j 4" --dbname myProjectdb --dbaddress 192.168.1.2 --dbport 5432
~~~~~~~~~~~~~~~~~~~~~

## 4. `checkers` mode

List the checkers available in the installed analyzers which can be used when
performing an analysis.

### Old `CodeChecker checkers` command

The ```+``` (or ```-```) sign before a name of a checker shows whether the
checker is enabled (or disabled) by default.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker checkers [-h] [--analyzers ANALYZERS [ANALYZERS ...]]
                            [--verbose {info,debug,debug_analyzer}]

optional arguments:
  -h, --help            show this help message and exit
  --analyzers ANALYZERS [ANALYZERS ...]
                        Select which analyzer checkers should be listed.
                        Currently supported analyzers: clangsa clang-tidy
                        (default: None)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

### New `codechecker-checkers` command

By default, `codechecker-checkers` will list all checkers, one per each row,
providing a quick overview on which checkers are available in the analyzers.

~~~~~~~~~~~~~~~~~~~~~
usage: codechecker-checkers [-h] [--analyzers ANALYZER [ANALYZER ...]]
                            [--details] [--only-enabled | --only-disabled]
                            [-o {rows,table,csv,json}]
                            [--verbose {info,debug,debug_analyzer}]

Get the list of checkers available and their enabled status in the supported
analyzers. Currently supported analyzers are: clangsa, clang-tidy.

optional arguments:
  -h, --help            show this help message and exit
  --analyzers ANALYZER [ANALYZER ...]
                        Show checkers only from the analyzers specified.
  --details             Show details about the checker, such as description,
                        if available. (default: False)
  --only-enabled        Show only the enabled checkers. (default: False)
  --only-disabled       Show only the disabled checkers. (default: False)
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        The format to list the applicable checkers as.
                        (default: rows)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

The list provided by default is formatted for easy machine and human
reading. Use the `--only-` options (`--only-enabled` and `--only-disabled`) to
filter the list if you wish to see just the enabled/disabled checkers.

A detailed view of the available checkers is available via `--details`. In the
*detailed view*, checker status, severity and description (if available) is
also printed.

A machine-readable `csv` or `json` output can be generated by supplying the
`--output csv` or `--output json` argument.

The _default_ list of enabled and disabled checkers can be altered by editing
`{INSTALL_DIR}/config/config.json`. Note, that this file is overwritten when
the package is reinstalled!

## 5. `analyzers` mode

List the available and supported analyzers installed on the system. This command
can be used to retrieve the to-be-used analyzers' install path and version
information.

By default, this command only lists the names of the available analyzers (with
respect to the environment CodeChecker is ran in).

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker analyzers [-h] [-a] [--details] [-o {rows,table,csv,json}]
                             [--verbose {info,debug,debug_analyzer}]

Get the list of available and supported analyzers, querying their version and
actual binary executed.

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             Show all supported analyzers, not just the available
                        ones. (default: False)
  --details             Show details about the analyzers, not just their
                        names. (default: False)
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        Specify the format of the output list. (default: rows)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

A detailed view of the available analyzers is available via `--details`. In the
*detailed view*, version string and install path is also printed.

A machine-readable `csv` or `json` output can be generated by supplying the
`--output csv` or `--output json` argument.

## 5. cmd mode:

A lightweigh command line interface to query the results of an analysis.
It is a suitable client to integrate with continuous integration, schedule maintenance tasks and verifying correct analysis process.
The commands always need a viewer port of an already running CodeChecker server instance (which can be started using CodeChecker server command).

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd [-h] {runs,results,sum,del} ...

positional arguments:
  {runs,results,diff,sum,del}
    runs                Get the run data.
    results             List results.
    diff                Diff two runs.
    sum                 Summarize the results of the run.
    del                 Remove run results.

optional arguments:
  -h, --help            show this help message and exit
~~~~~~~~~~~~~~~~~~~~~
## 6. plist mode:
Clang Static Analyzer's scan-build script can generate analyis output into plist xml files. 
In this You can import these files into the database.
You will need to specify containing the plist files afther the -d option.

Example:
~~~~~~~~~~~~~~~~~~~~~
CodeChecker plist -d ./results_plist -n myresults
~~~~~~~~~~~~~~~~~~~~~


## 7. debug mode:

In debug mode CodeChecker can generate logs for failed build actions. The logs can be helpful debugging the checkers.

## Example Usage

### Checking files

Checking with some extra checkers disabled and enabled

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -w ~/Develop/workspace -j 4 -b "cd ~/Libraries/myproject && make clean && make -j4" -s ~/Develop/skip.list -u ~/Develop/suppress.txt -e unix.Malloc -d core.uninitialized.Branch  -n MyLittleProject -c --dbport 5432 --dbname cctestdb
~~~~~~~~~~~~~~~~~~~~~

### View results

To view the results CodeChecker sever needs to be started.

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server -w ~/codes/package/checker_ws/ --dbport 5432 --dbaddress localhost
~~~~~~~~~~~~~~~~~~~~~

After the server has started open the outputed link to the browser (localhost:8001 in this example).

~~~~~~~~~~~~~~~~~~~~~
[11318] - WARNING! No suppress file was given, suppressed results will be only stored in the database.
[11318] - Checking for database
[11318] - Database is not running yet
[11318] - Starting database
[11318] - Waiting for client requests on [localhost:8001]
~~~~~~~~~~~~~~~~~~~~~

### Run CodeChecker distributed in a cluster

You may want to configure CodeChecker to do the analysis on separate machines in a distributed way.
Start the postgres database on a central machine (in this example it is called codechecker.central) on a remotely accessible address and port and then run
```CodeChecker check``` on multiple machines (called host1 and host2), specify the remote dbaddress and dbport and use the same run name.

Create and start an empty database to which the CodeChecker server can connect.

#### Setup PostgreSQL (one time only)

Before the first use, you have to setup PostgreSQL.
PostgreSQL stores its data files in a data directory, so before you start the PostgreSQL server you have to create and init this data directory.
I will call the data directory to pgsql_data.

Do the following steps:

~~~~~~~~~~~~~~~~~~~~~
# on machine codechecker.central

mkdir -p /path/to/pgsql_data
initdb -U codechecker -D /path/to/pgsql_data -E "SQL_ASCII"
# Start PostgreSQL server on port 5432
postgres -U codechecker -D /path/to/pgsql_data -p 5432 &>pgsql_log &
~~~~~~~~~~~~~~~~~~~~~

#### Run CodeChecker on multiple hosts

Then you can run CodeChecker on multiple hosts but using the same run name (in this example this is called "distributed_run".
postgres is listening on codechecker.central port 9999.

~~~~~~~~~~~~~~~~~~~~~
# On host1 we check module1
CodeChecker check -w /tmp/codechecker_ws -b "cd module_1;make" --dbport 5432 --dbaddress codechecker.central -n distributed_run

# On host2 we check module2
CodeChecker check -w /tmp/codechecker_ws -b "cd module_2;make" --dbport 5432 --dbaddress codechecker.central -n disributed_run
~~~~~~~~~~~~~~~~~~~~~


#### PostgreSQL authentication (optional)

If a CodeChecker is run with a user that needs database authentication, the
PGPASSFILE environment variable should be set to a pgpass file
For format and further information see PostgreSQL documentation:
http://www.postgresql.org/docs/current/static/libpq-pgpass.html

## Debugging CodeChecker

Command line flag can be used to turn in CodeChecker debug mode. The different
subcommands can be given a `-v` flag which needs a parameter. Possible values
are `debug`, `debug_analyzer` and `info`. Default is `info`.

`debug_analyzer` switches analyzer related logs on:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -n <name> -b <build_command> --verbose debug_analyzer
~~~~~~~~~~~~~~~~~~~~~

Turning on CodeChecker debug level logging is possible for the most subcommands:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -n <name> -b <build_command> --verbose debug
CodeChecker server -v <view_port> --verbose debug
~~~~~~~~~~~~~~~~~~~~~

If debug logging is enabled and PostgreSQL database is used, PostgreSQL logs are written to postgresql.log in the workspace directory.

Turn on SQL_ALCHEMY debug level logging

~~~~~~~~~~~~~~~~~~~~~
export CODECHECKER_ALCHEMY_LOG=True
~~~~~~~~~~~~~~~~~~~~~
