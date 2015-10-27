#CodeChecker Userguide

##CodeChecker usage

First of all, you have to setup the environment for CodeChecker.
Codechecker server uses PostgreSQL database to store the results which is also packed into the package.

~~~~~~~~~~~~~~~~~~~~~
cd $CODECHECKER_PACKAGE_ROOT/init
source init.sh
~~~~~~~~~~~~~~~~~~~~~

After sourcing the init script the 'CodeChecker --help' command should be available.


The next step is to start the CodeChecker main script.
The main script can be started with different options.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker.py [-h] {check,log,checkers,server,cmd,debug} ...

Run the codechecker script.

positional arguments:
  {check,log,checkers,server,cmd,debug}
                        commands
    check               Run codechecker for a project.
    log                 Build the project and only create a log file (no
                        checking).
    checkers            List available checkers.
    server              Start the codechecker database server.
    cmd                 Command line client
    debug               Create debug logs for failed actions

optional arguments:
  -h, --help            show this help message and exit
~~~~~~~~~~~~~~~~~~~~~


##Default configuration:

Used ports:
* 8764  - PostgreSql
* 11444 - CodeChecker result viewer

## 1. log mode:

Just build your project and create a log file but do not invoke the source code analysis.

~~~~~~~~~~~~~~~~~~~~~
$CodeChecker log --help
usage: CodeChecker.py log [-h] -o LOGFILE -b COMMAND

optional arguments:
  -h, --help            show this help message and exit
  -o LOGFILE, --output LOGFILE
                        Path to the log file.
  -b COMMAND, --build COMMAND
                        Build command.
~~~~~~~~~~~~~~~~~~~~~

You can change the compilers that should be logged.
Set CC_LOGGER_GCC_LIKE environment variable to a colon separated list.
For example (default):
~~~~~~~~~~~~~~~~~~~~~
export CC_LOGGER_GCC_LIKE="gcc:g++:clang"
~~~~~~~~~~~~~~~~~~~~~

Example:
~~~~~~~~~~~~~~~~~~~~~
CodeChecker log -o ../codechecker_myProject_build.log -b "make -j2"
~~~~~~~~~~~~~~~~~~~~~

Note:
In case you want to analyze your whole project, do not forget to clean your build tree before logging.

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
CodeChecker check --help
usage: CodeChecker.py check [-h] -w WORKSPACE -n NAME
                            (-b COMMAND | -l LOGFILE) [-j JOBS]
                            [-f CONFIGFILE] [-s SKIPFILE] [-u SUPPRESS]
                            [-e ENABLE] [-d DISABLE] [-c]
                            [--dbaddress DBADDRESS] [--dbport DBPORT]
                            [--dbname DBNAME] [--dbusername DBUSERNAME]
                            [--update]

optional arguments:
  -h, --help            show this help message and exit
  -w WORKSPACE, --workspace WORKSPACE
                        Directory where the codechecker can store analysis
                        related data.
  -n NAME, --name NAME  Name of the project.
  -b COMMAND, --build COMMAND
                        Build command.
  -l LOGFILE, --log LOGFILE
                        Path to the log file which is created during the
                        build.
  -j JOBS, --jobs JOBS  Number of jobs.
  -f CONFIGFILE, --config CONFIGFILE
                        Config file for the checkers.
  -s SKIPFILE, --skip SKIPFILE
                        Path to skip file.
  -u SUPPRESS, --suppress SUPPRESS
                        Path to suppress file.
  -e ENABLE, --enable ENABLE
                        Enable checker.
  -d DISABLE, --disable DISABLE
                        Disable checker.
  --keep-tmp            Keep temporary report files after sending data to
                        database storage server.
  --dbaddress DBADDRESS
                        Postgres database server address.
  --dbport DBPORT       Postgres database server port.
  --dbname DBNAME       Name of the database.
~~~~~~~~~~~~~~~~~~~~~

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

### Suppress file:

~~~~~~~~~~~~~~~~~~~~~
-u SUPPRESS
~~~~~~~~~~~~~~~~~~~~~

Suppress file can contain bug hashes and comments.
Suppressed bugs will not be showed in the viewer by default.
Usually a reason to suppress a bug is a false positive result (reporting a non-existent bug). Such false positives should be reported, so we can fix the checkers.
A comment can be added to suppressed reports that describes why that report is false positive. You should not edit suppress file by hand. The server should handle it.
The suppress file can be checked into the source code repository.
Bugs can be suppressed on the viewer even when suppress file was not set by command line arguments. This case the suppress will not be permanent. For this reason it is
advised to always provide (the same) suppress file for the checks.

### Skip file:

~~~~~~~~~~~~~~~~~~~~~
-s SKIPFILE, --skip SKIPFILE
~~~~~~~~~~~~~~~~~~~~~
With a skip file you can filter which files should or shouldn't be checked.
Each line in a skip file should start with a '-' or '+' character followed by a path glob pattern. A minus character means that if a checked file path - including the headers - matches with the pattern, the file will not be checked. The plus character means the opposite: if a file path matches with the pattern, it will be checked.
CodeChecker reads the file from top to bottom and stops at the first matching pattern.

For example:
~~~~~~~~~~~~~~~~~~~~~
-/skip/all/source/in/directory*
-/do/not/check/this.file
+/dir/check.this.file
-/dir/*
~~~~~~~~~~~~~~~~~~~~~

###Enable/Disable checkers

~~~~~~~~~~~~~~~~~~~~~
-e ENABLE, --enable ENABLE
-d DISABLE, --disable DISABLE
~~~~~~~~~~~~~~~~~~~~~
You can enable or disable checkers or checker groups. If you want to enable more checker groups use -e multiple times. To get the actual list of checkers run ```CodeChecer checkers``` command.
For example if you want to enable core and security checkers, but want to disable alpha checkers use

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -e core -e security -d alpha ...
~~~~~~~~~~~~~~~~~~~~~

###Multithreaded Checking

~~~~~~~~~~~~~~~~~~~~~
-j JOBS, --jobs JOBS  Number of jobs.
~~~~~~~~~~~~~~~~~~~~~
CodeChecker will execute analysis on as many threads as specified after -j argument.


###Various deployment possibilities

The codechecker server can be started separately when desired.
In that case multiple clients can use the same database to store new results or view old ones.


#### Codechecker server and database on the same machine

Codechecker server and the database are running on the same machine but the database server is started manually.
In this case the database handler and the database can be started manually by running the server command.
The workspace needs to be provided for both the server and the check commands.

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server -w ~/codechecker_wp --dbname myProjectdb --dbport 8764 --dbaddress localhost --view-port 11443
~~~~~~~~~~~~~~~~~~~~~

The checking process can be started separately on the same machine
~~~~~~~~~~~~~~~~~~~~~
CodeChecker check  -w ~/codechecker_wp -n myProject -b "make -j 4" --dbname myProjectdb --dbaddress localhost --dbport 8764
~~~~~~~~~~~~~~~~~~~~~

or on a different machine
~~~~~~~~~~~~~~~~~~~~~
CodeChecker check  -w ~/codechecker_wp -n myProject -b "make -j 4" --dbname myProjectdb --dbaddress 192.168.1.1 --dbport 8764
~~~~~~~~~~~~~~~~~~~~~


#### Codechecker server and database are on different machines

It is possible that the codechecker server and the PostgreSQL database that contains the analysis results are on different machines. To setup PostgreSQL see later section.

In this case the codechecker server can be started using the following command:
~~~~~~~~~~~~~~~~~~~~~
CodeChecker server --dbname myProjectdb --dbport 8764 --dbaddress 192.168.1.2 --view-port 11443
~~~~~~~~~~~~~~~~~~~~~
Start codechecker server locally which connects to a remote database (which is started separately). Workspace is not required in this case.


Start the checking as explained previously.
~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -w ~/codechecker_wp -n myProject -b "make -j 4" --dbname myProjectdb --dbaddress 192.168.1.2 --dbport 8764
~~~~~~~~~~~~~~~~~~~~~


## 3. checkers mode:

List all available checkers.

~~~~~~~~~~~~~~~~~~~~~
CodeChecker checkers
~~~~~~~~~~~~~~~~~~~~~


## 4. cmd mode:

A lightweigh command line interface to query the results of an analysis.
It is a suitable client to integrate with continous integration, schedule maintenance tasks and verifying correct analysis process.
The commands always need a viewer port of an already running CodeChecker server instance (which can be started using CodeChecker server command).

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker.py cmd [-h] {runs,results,sum,del} ...

positional arguments:
  {runs,results,sum,del}
    runs                Get the run data.
    results             List results.
    sum                 Sum results.
    del                 Remove run results.

optional arguments:
  -h, --help            show this help message and exit
~~~~~~~~~~~~~~~~~~~~~

## 5. debug mode:

In debug mode CodeChecker can generate logs for failed build actions. The logs can be helpful debugging the checkers.

## Example Usage

### Checking files

Checking with some extra checkers disabled and enabled

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check -w ~/Develop/workspace -j 4 -b "cd ~/Libraries/myproject && make clean && make -j4" -s ~/Develop/skip.list -u ~/Develop/suppress.txt -e unix.Malloc -d core.uninitialized.Branch  -n MyLittleProject -c --dbport 9999 --dbname cctestdb
~~~~~~~~~~~~~~~~~~~~~

### View results

To view the results CodeChecker sever needs to be started.

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server -w ~/codes/package/checker_ws/ --dbport 8764 --dbaddress localhost --view-port 11443
~~~~~~~~~~~~~~~~~~~~~

After the server has started open the outputed link to the browser (localhost:11443 in this example).

~~~~~~~~~~~~~~~~~~~~~
[11318] - WARNING! No suppress file was given, suppressed results will be only stored in the database.
[11318] - Checking for database
[11318] - Database is not running yet
[11318] - Starting database
[11318] - Waiting for client requests on [localhost:11443]
~~~~~~~~~~~~~~~~~~~~~

### Run CodeChecker distributed in a cluster

You may want to configure codechecker to do the analysis on separate machines in a distributed way.
Start the postgres database on a central machine (in this example it is called codechecker.central) on a remotely accessible address and port and then run 
```CodeChecker check``` on multiple machines (called host1 and host2), specify the remote dbaddress and dbport and use the same run name.

Create and start an empty database to which the codechecker server can connect.

#### Setup PostgreSQL (one time only)

Before the first use, you have to setup PostgreSQL.
PostgreSQL stores its data files in a data directory, so before you start the PostgreSQL server you have to create and init this data directory.
I will call the data directory to pgsql_data.

Do the following steps:
~~~~~~~~~~~~~~~~~~~~~
#on machine codechecker.central

mkdir -p /path/to/pgsql_data
initdb -U codechecker -D /path/to/pgsql_data -E "SQL_ASCII"
# Start PostgreSQL server on port 8764
postgres -U codechecker -D /path/to/pgsql_data -p 9999 &>pgsql_log &
~~~~~~~~~~~~~~~~~~~~~

#### Run CodeChecker on multiple hosts

Then you can run codechecker on multiple hosts but using the same run name (in this example this is called "distributed_run". 
You will need to use the -–update (incremental mode) to reuse the same run name. In this example it is assumed that 
postgres is listening on codechecker.central port 9999.
~~~~~~~~~~~~~~~~~~~~~
#On host1 we check module1
CodeChecker check -w /tmp/codechecker_ws -b "cd module_1;make" --dbport 9999 --dbaddress codechecker.central -n distributed_run --update

#On host2 we check module2 
CodeChecker check -w /tmp/codechecker_ws -b "cd module_2;make" --dbport 9999 --dbaddress codechecker.central -n disributed_run --update
~~~~~~~~~~~~~~~~~~~~~


#### PostgreSQL authentication (optional)

If a CodeChecker is run with a user that needs database authentication, the
PGPASSFILE environment variable should be set to a pgpass file
For format and further information see PostgreSQL documentation:
http://www.postgresql.org/docs/current/static/libpq-pgpass.html

##Debugging CodeChecker

Environment variables can be used to turn on CodeChecker debug mode.

Turn on CodeChecker debug level logging
~~~~~~~~~~~~~~~~~~~~~
export CODECHECKER_VERBOSE=debug
~~~~~~~~~~~~~~~~~~~~~

Turn on SQL_ALCHEMY debug level logging
~~~~~~~~~~~~~~~~~~~~~
export CODECHECKER_ALCHEMY_LOG=True
~~~~~~~~~~~~~~~~~~~~~
