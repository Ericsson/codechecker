# CodeChecker

First of all, you have to setup the environment for CodeChecker.
CodeChecker uses SQLite database (by default) to store the results
which is also packed into the package.

Running CodeChecker is via its main invocation script, `CodeChecker`:

~~~~~~~~~~~~~~~~~~~~~
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

Example scenario: Analyzing, and storing results
------------------------------------------------
Start the server where the results will be stored and can be viewed
after the analysis is done:
    CodeChecker server

Analyze a project with default settings:
    CodeChecker check -b "cd ~/myproject && make" -o "~/results"

Store the analyzer results to the server:
    CodeChecker store "~/results" -n myproject

The results can be viewed:
 * In a web browser: http://localhost:8001
 * In the command line:
    CodeChecker cmd results myproject

Example scenario: Analyzing, and printing results to Terminal (no storage)
--------------------------------------------------------------------------
In this case, no database is used, and the results are printed on the standard
output.

    CodeChecker check -b "cd ~/myproject && make"
~~~~~~~~~~~~~~~~~~~~~


## Default configuration

Used ports:

* `5432` - PostgreSQL
* `8001` - CodeChecker server

The server listens only on the local machine.

The initial product is called `Default`.

# Easy analysis wrappers

CodeChecker provides, along with the more fine-tuneable commands, some easy
out-of-the-box invocations to ensure the most user-friendly operation, the
**check** mode.

## `check`

It is possible to easily analyse the project for defects without keeping the
temporary analysis files and without using any database to store the reports
in, but instead printing the found issues to the standard output.

To analyse your project by doing a build and reporting every found issue in the
built files, execute

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check --build "make"
~~~~~~~~~~~~~~~~~~~~~

Please make sure your build command actually compiles (builds) the source
files you intend to analyse, as CodeChecker only analyzes files that had been
used by the build system.

If you have an already existing JSON Compilation Commands file, you can also
supply it to `check`:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check --logfile ./my-build.json
~~~~~~~~~~~~~~~~~~~~~

By default, only the report's main messages are printed. To print the
individual steps the analysers took in discovering the issue, specify
`--steps`.

`check` is a wrapper over the following calls:

 * If `--build` is specified, the build is executed as if `CodeChecker log`
   were invoked.
 * The resulting logfile, or a `--logfile` specified is used for `CodeChecker
   analyze`, which will put analysis reports into `--output`.
 * The analysis results are fed for `CodeChecker parse`.

After the results has been printed to the standard output, the temporary files
used for the analysis are cleaned up.

Please see the individual help for `log`, `analyze` and `parse` (below in this
_User guide_) for information about the arguments which are not documented
here. For example the CTU related arguments are documented at `analyze`
subcommand.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker check [-h] [-o OUTPUT_DIR] [-q] [-f]
                         (-b COMMAND | -l LOGFILE) [-j JOBS] [-i SKIPFILE]
                         [--analyzers ANALYZER [ANALYZER ...]]
                         [--add-compiler-defaults]
                         [--saargs CLANGSA_ARGS_CFG_FILE]
                         [--tidyargs TIDY_ARGS_CFG_FILE]
                         [-e checker/checker-group] [-d checker/checker-group]
                         [--print-steps]
                         [--verbose {info,debug,debug_analyzer}]

Run analysis for a project with printing results immediately on the standard
output. Check only needs a build command or an already existing logfile and
performs every step of doing the analysis in batch.

optional arguments:
  -h, --help
  -o OUTPUT_DIR, --output OUTPUT_DIR
                        Store the analysis output in the given folder. If it
                        is not given then the results go into a temporary
                        directory which will be removed after the analysis.
  -t {plist}, --type {plist}, --output-format {plist}
                        Specify the format the analysis results should use.
                        (default: plist)
  -q, --quiet           If specified, the build tool's and the analyzers'
                        output will not be printed to the standard output.
  -f, --force           Delete analysis results stored in the database for the
                        current analysis run's name and store only the results
                        reported in the 'input' files. (By default,
                        CodeChecker would keep reports that were coming from
                        files not affected by the analysis, and only
                        incrementally update defect reports for source files
                        that were analysed.)
  --verbose {info,debug,debug_analyzer}

log arguments:

  -b COMMAND, --build COMMAND
  -l LOGFILE, --logfile LOGFILE

analyzer arguments:

  -j JOBS, --jobs JOBS
  -c, --clean
  -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
  --analyzers ANALYZER [ANALYZER ...]
  --add-compiler-defaults
  --capture-analysis-output
  --saargs CLANGSA_ARGS_CFG_FILE
  --tidyargs TIDY_ARGS_CFG_FILE

cross translation unit analysis arguments:
  These arguments are only available if the Clang Static Analyzer supports
  Cross-TU analysis. By default, no CTU analysis is run when 'CodeChecker
  analyze' is called.

  --ctu, --ctu-all
  --ctu-collect
  --ctu-analyze
  --ctu-on-the-fly

checker configuration:

  -e checker/checker-group, --enable checker/checker-group
  -d checker/checker-group, --disable checker/checker-group

output arguments:
  --print-steps
~~~~~~~~~~~~~~~~~~~~~

# `PRODUCT_URL` format

Several subcommands, such as `store` and `cmd` need a connection specification
on which server and for which *Product* (read more [about
products](/docs/products.md)) an action, such as report storage or result
retrieving, should be done.

This is done via the `PRODUCT_URL` where indicated in the subcommand, which
contains the server's access protocol, address, and the to-be-used product's
unique endpoint. The format of this string is:
`[http[s]://]host:port/ProductEndpoint`. This URL looks like a standar Web
browsing (HTTP) request URL.

CodeChecker communicates via HTTP requests, thus the first part specifies
whether or not a more secure SSL/TLS-wrapped `https` protocol should be used.
If omitted, the default value is `http`. The second part is the host and the
port the server listens on. After a `/`, the unique endpoint of the product
must be given, this is case-sensitive. This unique endpoint is configured and
allocated when the [product is created](/docs/products.md), by the server's
administrators. The product must exist and be properly configured before any
normal operation could be done on it.

If no URL is specified, the default value `http://localhost:8001/Default` will
be used: a standard HTTP CodeChecker server running on the local machine, on
the default port, using the *Default* product.

## Example

The URL `https://codechecker.example.org:9999/SampleProduct` will access the
server machine `codechecker.example.org` trying to connect to a server
listening on port `9999` via HTTPS. The product `SampleProduct` will be used.


# Available CodeChecker commands

## 1. `log` mode

The first step in performing an analysis on your project is to record
information about the files in your project for the analyzers. This is done by
recording a build of your project, which is done by the command `CodeChecker
log`.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker log [-h] -o LOGFILE -b COMMAND [-q]
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
  -q, --quiet           Do not print the output of the build tool into the
                        output of this command.
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

Please note, that only the files that are used in the given `--build` argument
will be recorded. To analyze your whole project, make sure your build tree has
been cleaned before executing `log`.

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

## 2. `analyze` mode

After a JSON Compilation Command Database has been created, the next step is
to invoke and execute the analyzers. CodeChecker will use the specified
`logfile`s (there can be multiple given) and create the outputs to the
`--output` directory. (These outputs will be `plist` files, currently only
these are supported.) The machine-readable output files can be used later on
for printing an overview in the terminal (`CodeChecker parse`) or storing
(`CodeChecker store`) analysis results in a database, which can later on be
viewed in a browser.

Example:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker analyze ../codechecker_myProject_build.log -o my_plists
~~~~~~~~~~~~~~~~~~~~~

`CodeChecker analyze` supports a myriad of fine-tuning arguments, explained
below:

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker analyze [-h] [-j JOBS] [-i SKIPFILE] -o OUTPUT_PATH
                           [-t {plist}] [-q] [-c] [-n NAME]
                           [--analyzers ANALYZER [ANALYZER ...]]
                           [--add-compiler-defaults]
                           [--capture-analysis-output]
                           [--saargs CLANGSA_ARGS_CFG_FILE]
                           [--tidyargs TIDY_ARGS_CFG_FILE]
                           [-e checker/checker-group]
                           [-d checker/checker-group] [--enable-all]
                           [--verbose {info,debug,debug_analyzer}]
                           logfile [logfile ...]

Use the previously created JSON Compilation Database to perform an analysis on
the project, outputting analysis results in a machine-readable format.

positional arguments:
  logfile               Path to the JSON compilation command database files
                        which were created during the build. The analyzers
                        will check only the files registered in these build
                        databases.

optional arguments:
  -h, --help            show this help message and exit
  -j JOBS, --jobs JOBS  Number of threads to use in analysis. More threads
                        mean faster analysis at the cost of using more memory.
                        (default: 1)
  -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                        Path to the Skipfile dictating which project files
                        should be omitted from analysis. Please consult the
                        User guide on how a Skipfile should be laid out.
  -o OUTPUT_PATH, --output OUTPUT_PATH
                        Store the analysis output in the given folder.
  -t {plist}, --type {plist}, --output-format {plist}
                        Specify the format the analysis results should use.
                        (default: plist)
  -q, --quiet           Do not print the output or error of the analyzers to
                        the standard output of CodeChecker.
  -c, --clean           Delete analysis reports stored in the output
                        directory. (By default, CodeChecker would keep reports
                        and overwrites only those files that were update by
                        the current build command).
  -n NAME, --name NAME  Annotate the run analysis with a custom name in the
                        created metadata file.
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

### _Skip_ file

~~~~~~~~~~~~~~~~~~~~~
-s SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                      Path to the Skipfile dictating which project files
                      should be omitted from analysis.
~~~~~~~~~~~~~~~~~~~~~

Skipfiles filter which files should or should not be analyzed. CodeChecker
reads the skipfile from top to bottom and stops at the first matching pattern
when deciding whether or not a file should be analyzed.

Each line in the skip file begins with a `-` or a `+`, followed by a path glob
pattern. `-` means that if a file matches a pattern it should **not** be
checked, `+` means that it should be.

#### Example

~~~~~~~~~~~~~~~~~~~~~
-/skip/all/files/in/directory/*
-/do/not/check/this.file
+/dir/do.check.this.file
-/dir/*
~~~~~~~~~~~~~~~~~~~~~

In the above example, every file under `/dir` **will be** skipped, except the
one explicitly specified to **be analyzed** (`/dir/do.check.this.file`).

### Analyzer configuration

~~~~~~~~~~~~~~~~~~~~~
analyzer arguments:
  --analyzers ANALYZER [ANALYZER ...]
                        Run analysis only with the analyzers specified.
                        Currently supported analyzers are: clangsa, clang-
                        tidy.
  --add-compiler-defaults
                        Retrieve compiler-specific configuration from the
                        compilers themselves, and use them with Clang. This is
                        used when the compiler on the system is special, e.g.
                        when doing cross-compilation.
  --capture-analysis-output
                        Store standard output and standard error of successful
                        analyzer invocations into the '<OUTPUT_DIR>/success'
                        directory.
  --saargs CLANGSA_ARGS_CFG_FILE
                        File containing argument which will be forwarded
                        verbatim for the Clang Static Analyzer.
  --tidyargs TIDY_ARGS_CFG_FILE
                        File containing argument which will be forwarded
                        verbatim for Clang-Tidy.
~~~~~~~~~~~~~~~~~~~~~

CodeChecker supports several analyzer tools. Currently, these analyzers are
the [_Clang Static Analyzer_](http://clang-analyzer.llvm.org) and
[_Clang-Tidy_](http://clang.llvm.org/extra/clang-tidy). `--analyzers` can be
used to specify which analyzer tool should be used (by default, all supported
are used). The tools are completely independent, so either can be omitted if
not present as they are provided by different binaries.

#### Compiler-specific include path and define detection (cross compilation)

Some of the include paths are hardcoded during compiler build. If a (cross)
compiler is used to build a project it is possible that the wrong include
paths are searched and the wrong headers will be included which causes
analyses to fail. These hardcoded include paths and defines can be marked for
automatically detection by specifying the `--add-compiler-defaults` flag.

CodeChecker will get the hardcoded values for the compilers set in the
`CC_LOGGER_GCC_LIKE` environment variable.

~~~~~~~~~~~~~~~~~~~~~
export CC_LOGGER_GCC_LIKE="gcc:g++:clang"
~~~~~~~~~~~~~~~~~~~~~

If there are still compilation errors after using the `--add-compiler-defaults`
argument, it is possible that the wrong build target architecture
(32bit, 64bit) is used. Please try to forward these compilation flags
to the analyzers:

 - `-m32` (32-bit build)
 - `-m64` (64-bit build)

#### Forwarding compiler options

Forwarded options can modify the compilation actions logged by the build logger
or created by CMake (when exporting compile commands). The extra compiler
options can be given in config files which are provided by the flags
described below.

The config files can contain placeholders in `$(ENV_VAR)` format. If the
`ENV_VAR` environment variable is set then the placeholder is replaced to its
value. Otherwise an error message is logged saying that the variable is not
set, and in this case an empty string is inserted in the place of the
placeholder.

##### _Clang Static Analyzer_

Use the `--saargs` argument to a file which contains compilation options.

~~~~
CodeChecker analyze mylogfile.json --saargs extra_sa_compile_flags.txt -n myProject
~~~~

Where the `extra_sa_compile_flags.txt` file contains additional compilation
options, for example:

~~~~~
-I~/include/for/analysis -I$(MY_LIB)/include -DDEBUG
~~~~~

(where `MY_LIB` is the path of a library code)

##### _Clang-Tidy_

Use the `--tidyargs` argument to a file which contains compilation options.

~~~~
CodeChecker analyze mylogfile.json --tidyargs extra_tidy_compile_flags.txt -n myProject
~~~~

Where the `extra_tidy_compile_flags.txt` file contains additional compilation
flags.

Clang-Tidy requires a different format to add compilation options.
Compilation options can be added before (`-extra-arg-before=<string>`) and
after (`-extra-arg=<string>`) the original compilation options.

Example:

~~~~
-extra-arg-before='-I~/include/for/analysis' -extra-arg-before='-I~/other/include/for/analysis/' -extra-arg-before='-I$(MY_LIB)/include' -extra-arg='-DDEBUG'
~~~~

(where `MY_LIB` is the path of a library code)

### Toggling checkers

The list of checkers to be used in the analysis can be fine-tuned with the
`--enable` and `--disable` options. See `codechecker-checkers` for the list of
available checkers in the binaries installed on your system.

~~~~~~~~~~~~~~~~~~~~~
checker configuration:

  -e checker/checker-group, --enable checker/checker-group
                        Set a checker (or checker group) to BE USED in the
                        analysis.
  -d checker/checker-group, --disable checker/checker-group
                        Set a checker (or checker group) to BE PROHIBITED from
                        use in the analysis.
  --enable-all          Force the running analyzers to use almost every
                        checker available. The checker groups 'alpha.',
                        'debug.' and 'osx.' (on Linux) are NOT enabled
                        automatically and must be EXPLICITLY specified.
                        WARNING! Enabling all checkers might result in the
                        analysis losing precision and stability, and could
                        even result in a total failure of the analysis. USE
                        WISELY AND AT YOUR OWN RISK!
~~~~~~~~~~~~~~~~~~~~~

Both `--enable` and `--disable` take individual checkers or checker groups as
their argument and there can be any number of such flags specified.

For example

~~~
--enable core --disable core.uninitialized --enable core.uninitialized.Assign
~~~

will enable every `core` checker which is not `core.uninitialized`, but
`core.uninitialized.Assign` will also be enabled.

Disabling certain checkers - such as the `core` group - is unsupported by
the LLVM/Clang community, and thus discouraged.

#### `--enable-all`

Specifying `--enable-all` will "force" CodeChecker to enable **every** checker
available in the analyzers. This presents an easy shortcut to force such an
analysis without the need of editing configuration files or supplying long
command-line arguments. However, `--enable-all` *might* result in the analysis
losing stability and precision, and worst case, might result in a complete and
utter failure in the analysis itself. **`--enable-all` may only be used at
your own risk!**

Even specifying `--enable-all` will **NOT** enable checkers from some special
checker groups, such as `alpha.` and `debug.`. `osx.` checkers are only enabled
if CodeChecker is run on a macOS machine. `--enable-all` can further be
fine-tuned with subsequent `--enable` and `--disable` arguments, for example

~~~~
--enable-all --enable alpha --disable misc
~~~~

can be used to "further" enable `alpha.` checkers, and disable `misc` ones.

### Cross Translation Unit (CTU) analysis mode

If the `clang` static analyzer binary in your installation supports
[Cross Translation Unit analysis](http://llvm.org/devmtg/2017-03//2017/02/20/accepted-sessions.html#7),
CodeChecker can execute the analyzers with this mode enabled.

These options are only visible in `analyze` if CTU support is present. CTU
mode uses some extra storage space under the specified `--output-dir`.

~~~~~~~~~~~~~~~~~~~~~
cross translation unit analysis arguments:
  These arguments are only available if the Clang Static Analyzer supports
  Cross-TU analysis. By default, no such analysis is run when 'CodeChecker
  analyze' is called.

  --ctu, --ctu-all      Perform Cross Translation Unit (CTU) analysis, both
                        'collect' and 'analyze' phases. In this mode, the
                        extra files created by 'collect' are cleaned up after
                        the analysis.
  --ctu-collect         Perform the first, 'collect' phase of Cross-TU
                        analysis. This phase generates extra files needed by
                        CTU analysis, and puts them into '<OUTPUT_DIR>/ctu-
                        dir'. NOTE: If this argument is present, CodeChecker
                        will NOT execute the analyzers!
  --ctu-analyze         Perform the second, 'analyze' phase of Cross-TU
                        analysis, using already available extra files in
                        '<OUTPUT_DIR>/ctu-dir'. (These files will not be
                        cleaned up in this mode.)
  --ctu-on-the-fly      If specified, the 'collect' phase will not create the
                        extra AST dumps, but rather analysis will be run with
                        an in-memory recompilation of the source files.
~~~~~~~~~~~~~~~~~~~~~

## 3. `parse` mode

`parse` is used to read previously created machine-readable analysis results
(such as `plist` files), usually previously generated by `CodeChecker analyze`.
`parse` prints analysis results to the standard output.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker parse [-h] [-t {plist}] [--suppress SUPPRESS]
                         [--export-source-suppress] [--print-steps]
                         [--verbose {info,debug,debug_analyzer}]
                         [file/folder [file/folder ...]]

Parse and pretty-print the summary and results from one or more 'codechecker-
analyze' result files.

positional arguments:
  file/folder           The analysis result files and/or folders containing
                        analysis results which should be parsed and printed.
                        (default: /home/<username>/.codechecker/reports)

optional arguments:
  -h, --help            show this help message and exit
  -t {plist}, --type {plist}, --input-format {plist}
                        Specify the format the analysis results were created
                        as. (default: plist)
  --suppress SUPPRESS   Path of the suppress file to use. Records in the
                        suppress file are used to suppress the display of
                        certain results when parsing the analyses' report.
                        (Reports to an analysis result can also be suppressed
                        in the source code -- please consult the manual on how
                        to do so.) NOTE: The suppress file relies on the "bug
                        identifier" generated by the analyzers which is
                        experimental, take care when relying on it.
  --export-source-suppress
                        Write suppress data from the suppression annotations
                        found in the source files that were analyzed earlier
                        that created the results. The suppression information
                        will be written to the parameter of '--suppress'.
  --print-steps         Print the steps the analyzers took in finding the
                        reported defect.
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

For example, if the analysis was run like:

~~~~
CodeChecker analyze ../codechecker_myProject_build.log -o my_plists
~~~~

then the results of the analysis can be printed with

~~~~
CodeChecker parse ./my_plists
~~~~

### Suppression in the source code

Suppress comments can be used in the source files to suppress specific or all
checker results found in a particular line of code. Suppress comment should be
above the line where the defect was found, and no empty lines are allowed
between the line with the bug and the suppress comment.

Only comment lines staring with `//` are supported!

#### Supported formats

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

#### Exporting source code suppression to suppress file

~~~~~~~~~~~~~~~~~~~~~
  --export-source-suppress
                        Write suppress data from the suppression annotations
                        found in the source files that were analyzed earlier
                        that created the results.
~~~~~~~~~~~~~~~~~~~~~

~~~~
CodeChecker parse ./my_plists --suppress generated.suppress --export-source-suppress
~~~~

## 4. `store` mode

A `Codechecker server` needs to be started before the reports can be stored to
a database.

`store` is used to save previously created machine-readable analysis results
(such as `plist` files), usually previously generated by `CodeChecker analyze`
to the database.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker store [-h] [-t {plist}] [-n NAME] [--tag TAG] [-f]
                         [--url PRODUCT_URL]
                         [--verbose {info,debug,debug_analyzer}]
                         [file/folder [file/folder ...]]

Store the results from one or more 'codechecker-analyze' result files in a
database.

positional arguments:
  file/folder           The analysis result files and/or folders containing
                        analysis results which should be parsed and printed.
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
  -f, --force           Delete analysis results stored in the database for the
                        current analysis run's name and store only the results
                        reported in the 'input' files. (By default,
                        CodeChecker would keep reports that were coming from
                        files not affected by the analysis, and only
                        incrementally update defect reports for source files
                        that were analysed.)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)

server arguments:
  Specifies a 'CodeChecker server' instance which will be used to store the
  results. This server must be running and listening, and the given product
  must exist prior to the 'store' command being run.

  --url PRODUCT_URL     The URL of the product to store the results for, in
                        the format of '[http[s]://]host:port/Endpoint'.
                        (default: localhost:8001/Default)


The results can be viewed by connecting to such a server in a Web browser or
via 'CodeChecker cmd'.
~~~~~~~~~~~~~~~~~~~~~

For example, if the analysis was run like:

~~~~
CodeChecker analyze ../codechecker_myProject_build.log -o ./my_plists
~~~~

then the results of the analysis can be stored with this command:

~~~~
CodeChecker store ./my_plists -n my_project
~~~~

### Using SQLite for database

CodeChecker can also use SQLite for storing the results. In this case the
SQLite database will be created in the workspace directory.

In order to use PostgreSQL instead of SQLite, use the `--postgresql` command
line argument for `CodeChecker server` command.
If `--postgresql` is not given then SQLite is used by default in
which case `--dbport`, `--dbaddress`, `--dbname`, and
`--dbusername` command line arguments are ignored.

**NOTE!** Schema migration is not supported with SQLite. This means if you
upgrade your CodeChecker to a newer version, you might need to re-check your
project.

## 5. `checkers` mode

List the checkers available in the installed analyzers which can be used when
performing an analysis.

By default, `CodeChecker checkers` will list all checkers, one per each row,
providing a quick overview on which checkers are available in the analyzers.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker checkers [-h] [--analyzers ANALYZER [ANALYZER ...]]
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
                        if available.
  --only-enabled        Show only the enabled checkers.
  --only-disabled       Show only the disabled checkers.
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

## 6. `analyzers` mode

List the available and supported analyzers installed on the system. This command
can be used to retrieve the to-be-used analyzers' install path and version
information.

By default, this command only lists the names of the available analyzers (with
respect to the environment CodeChecker is run in).

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker analyzers [-h] [--all] [--details]
                             [-o {rows,table,csv,json}]
                             [--verbose {info,debug,debug_analyzer}]

Get the list of available and supported analyzers, querying their version and
actual binary executed.

optional arguments:
  -h, --help            show this help message and exit
  --all                 Show all supported analyzers, not just the available
                        ones.
  --details             Show details about the analyzers, not just their
                        names.
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        Specify the format of the output list. (default: rows)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

A detailed view of the available analyzers is available via `--details`. In the
*detailed view*, version string and install path is also printed.

A machine-readable `csv` or `json` output can be generated by supplying the
`--output csv` or `--output json` argument.

## 7. `server` mode

To view and store the analysis reports in a database, a `CodeChecker server`
must be started. This is done via the `server` command, which creates a
standard Web server and initializes or connects to a database with
the given configuration.

The CodeChecker Viewer server can be browsed by a Web browser by opening the
address of it (by default, [`http://localhost:8001`](http://localhost:8001)),
or via the `CodeChecker cmd` command-line client.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker server [-h] [-w WORKSPACE] [-f CONFIG_DIRECTORY]
                          [--host LISTEN_ADDRESS] [-v PORT] [--not-host-only]
                          [--sqlite SQLITE_FILE | --postgresql]
                          [--dbaddress DBADDRESS] [--dbport DBPORT]
                          [--dbusername DBUSERNAME] [--dbname DBNAME]
                          [--reset-root] [--force-authentication]
                          [-l | -s | --stop-all]
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
                        settings, and SSL certificates) from. 
                        (default: /home/<username>/.codechecker)
  --host LISTEN_ADDRESS
                        The IP address or hostname of the server on which it
                        should listen for connections. (default: localhost)
  -v PORT, --view-port PORT, -p PORT, --port PORT
                        The port which will be used as listen port for the
                        server. (default: 8001)
  --not-host-only       If specified, storing and viewing the results will be
                        possible not only by browsers and clients running
                        locally, but to everyone, who can access the server
                        over the Internet. (Equivalent to specifying '--host
                        ""'.) (default: False)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)

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
~~~~~~~~~~~~~~~~~~~~~

To start a server with default configuration, simply execute

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server
~~~~~~~~~~~~~~~~~~~~~

### Creating a public server

~~~~~~~~~~~~~~~~~~~~~
  --host LISTEN_ADDRESS
                        The IP address or hostname of the server on which it
                        should listen for connections. (default: localhost)
  --not-host-only       If specified, viewing the results will be possible not
                        only by browsers and clients running locally, but to
                        everyone, who can access the server over the Internet.
                        (Equivalent to specifying '--host ""'.) (default:
                        False)
~~~~~~~~~~~~~~~~~~~~~

By default, the running server can only be accessed from the same machine
(`localhost`) where it is running. This can be overridden by specifying
`--host ""`, instructing the server to listen on all available interfaces.

### Configuring database and server settings' location

The `--sqlite` (or `--postgresql` and the various `--db-` arguments) can be
used to specify where the database, containing the analysis reports is.

`--config-directory` specifies where the server configuration files, such as
[authentication config](authentication.md) is. For example, one can start
two servers with two different product layout, but with the same authorisation
configuration:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server --sqlite ~/major_bugs.sqlite -f ~/.codechecker -p 8001
CodeChecker server --sqlite ~/minor_bugs.sqlite -f ~/.codechecker -p 8002
~~~~~~~~~~~~~~~~~~~~~

The `--workspace` argument can be used to _shortcut_ this specification: by
default, the configuration directory is the _workspace_ itself, and therein
resides the `config.sqlite` file, containing the product configuration.

If the server is started in `--sqlite` mode and fresh, that is, no product
configuration file is found, a product named `Default`, using `Default.sqlite`
in the configuration directory is automatically created. Please see
[Product management](products.md) for details on how to configure products.

### Master superuser and authentication forcing

~~~~~~~~~~~~~~~~~~~~~
root account arguments:
  Servers automatically create a root user to access the server's
  configuration via the clients. This user is created at first start and
  saved in the CONFIG_DIRECTORY, and the credentials are printed to the
  server's standard output. The plaintext credentials are NEVER accessible
  again.

  --reset-root          Force the server to recreate the master superuser
                        (root) account name and password. The previous
                        credentials will be invalidated, and the new ones will
                        be printed to the standard output.
  --force-authentication
                        Force the server to run in authentication requiring
                        mode, despite the configuration value in
                        'session_config.json'. This is needed if you need to
                        edit the product configuration of a server that would
                        not require authentication otherwise.
~~~~~~~~~~~~~~~~~~~~~

### Enfore secure socket (SSL)

You can enforce SSL security on your listening socket. In this case all clients must
access your server using the `https://host:port` URL format.

To enable SSL simply place an SSL certificate to `<CONFIG_DIRECTORY>/cert.pem`
and the corresponding private key to `<CONFIG_DIRECTORY>/key.pem`.
You can generate these certificates for example 
using the [openssl tool](https://www.openssl.org/).
When the server finds these files upon start-up, 
SSL will be automatically enabled. 

### Managing running servers

~~~~~~~~~~~~~~~~~~~~~
running server management:
  -l, --list            List the servers that has been started by you.
  -s, --stop            Stops the server associated with the given view-port
                        and workspace.
  --stop-all            Stops all of your running CodeChecker server
                        instances.
~~~~~~~~~~~~~~~~~~~~~

CodeChecker servers can be started in the background as any other service, via
common shell tools such as `nohup` and `&!`. The running instances can be
queried via `--list`.

Calling `CodeChecker server --stop` will stop the "default" server, i.e. one
that was started by simply calling `CodeChecker server`. This _"stop"_ command
is equivalent to pressing `Ctrl`-`C` in the server's terminal, resulting in an
immediate termination of the server.

A server running on a specific and port can be stopped by:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker server -w ~/my_codechecker_workspace -p 8002 --stop
~~~~~~~~~~~~~~~~~~~~~

`--stop-all` will stop every running server that is printed by `--list`.

## 8. `cmd` mode

The `CodeChecker cmd` is a lightweight command line client that can be used to
view analysis results from the command-line. The command-line client can also
be integrated into a continuous integration loop or can be used to schedule
maintenance tasks.

Most of the features available in a Web browser opening the analysis result
viewer server on its port is available in the `cmd` tool.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd [-h]
                       {runs,results,diff,sum,del,suppress,products,login} ...

The command-line client is used to connect to a running 'CodeChecker server'
(either remote or local) and quickly inspect analysis results, such as runs,
individual defect reports, compare analyses, etc. Please see the invidual
subcommands for further details.

optional arguments:
  -h, --help            show this help message and exit

available actions:
  {runs,results,diff,sum,del,suppress,products,login}
    runs                List the available analysis runs.
    results             List analysis result (finding) summary for a given
                        run.
    diff                Compare two analysis runs and show the difference.
    sum                 Show number of reports per checker.
    del                 Delete analysis runs.
    suppress            Manage and export/import suppressions of a CodeChecker
                        server.
    products            Access subcommands related to configuring the products
                        managed by a CodeChecker server.
    login               Authenticate into CodeChecker servers that require
                        privileges.
~~~~~~~~~~~~~~~~~~~~~

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

~~~~~~~~~~~~~~~~~~~~~
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
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

### List runs (`runs`)

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd runs [-h] [--url PRODUCT_URL]
                            [-o {plaintext,rows,table,csv,json}]
                            [--verbose {info,debug,debug_analyzer}]

List the analysis runs available on the server.
~~~~~~~~~~~~~~~~~~~~~

### List analysis results' summary (`results`)

Prints basic information about analysis results, such as location, checker
name, summary.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd results [-h] RUN_NAME [-s] [--filter FILTER]
                               [--url PRODUCT_URL]
                               [-o {plaintext,rows,table,csv,json}]
                               [--verbose {info,debug,debug_analyzer}]
                               RUN_NAME

Show the individual analysis reports' summary.

positional arguments:
  RUN_NAME              Name of the analysis run to show result summaries of.
                        Use 'CodeChecker cmd runs' to get the available runs.

optional arguments:
  -h, --help            show this help message and exit
  -s, --suppressed      Show only suppressed results instead of only
                        unsuppressed ones. (default: False)
  --filter FILTER       Filter results. The filter string has the following
                        format:
                        [<SEVERITIES>]:[<CHECKER_NAMES>]:[<FILE_PATHS>] where
                        severites, checker_names, file_paths should be a comma
                        separated list, e.g.:
                        "high,medium:unix,core:*.cpp,*.h" (default: ::)
~~~~~~~~~~~~~~~~~~~~~

### Show differences between two runs (`diff`)

This mode shows analysis results (in the same format as `results`) does, but
from the comparison of two runs.

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd diff [-h] -b BASE_RUN -n NEW_RUN [-s] [--filter FILTER]
                            (--new | --resolved | --unresolved)
                            [--url PRODUCT_URL]
                            [-o {plaintext,rows,table,csv,json}]
                            [--verbose {info,debug,debug_analyzer}]

Compare two analysis runs to show the results that differ between the two.

optional arguments:
  -h, --help            show this help message and exit
  -b BASE_RUN, --basename BASE_RUN
                        The 'base' (left) side of the difference: this
                        analysis run is used as the initial state in the
                        comparison. The basename can be a Python regex which
                        is meant to cover the whole run name. So if you have
                        run_1_a_name, run_2_b_name and run_2_c_name then
                        run_.*_[ab]_name selects the first two.
  -n NEW_RUN, --newname NEW_RUN
                        The 'new' (right) side of the difference: this
                        analysis run is compared to the -b/--basename run.
                        The parameter can be a run name(on the remote server) 
                        or a local report directory (result of the analyze
                        command).
  -s, --suppressed      Filter results to only show suppressed entries.
                        (default: False)
  --filter FILTER       Filter results. The filter string has the following
                        format:
                        [<SEVERITIES>]:[<CHECKER_NAMES>]:[<FILE_PATHS>] where
                        severites, checker_names, file_paths should be a comma
                        separated list, e.g.:
                        "high,medium:unix,core:*.cpp,*.h" (default: ::)

comparison modes:
  --new                 Show results that didn't exist in the 'base' but
                        appear in the 'new' run.
  --resolved            Show results that existed in the 'base' but
                        disappeared from the 'new' run.
  --unresolved          Show results that appear in both the 'base' and the
                        'new' run.
~~~~~~~~~~~~~~~~~~~~~

The command can be used in *local* or *remote* compare modes.

In *local mode* the results of a local analysis (see `CodeChecker analyze`)
can be compared to the results stored (see `CodeChecker store`) on a remote
CodeChecker server:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker cmd diff -p 8001 --basename my_project --newname ./my_updated_plists --new
~~~~~~~~~~~~~~~~~~~~~

In *remote* compare mode, two runs stored on a remote CodeChecker server can
be compared to each other:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker cmd diff -p 8001 --basename my_project --newname my_new_checkin --new
~~~~~~~~~~~~~~~~~~~~~

There is opportunity to compare a run to multiple baselines. You can simply
provide a regular expression by `-b` flag which covers the required run names.
The Python regex syntax has to be used:
https://docs.python.org/2/library/re.html#regular-expression-syntax.

### Show summarised count of results (`sum`)

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd sum [-h] (-n RUN_NAME [RUN_NAME ...] | -a) [-s]
                           [--filter FILTER] [--url PRODUCT_URL]
                           [-o {plaintext,rows,table,csv,json}]
                           [--verbose {info,debug,debug_analyzer}]

Show checker statistics for some analysis runs.

optional arguments:
  -h, --help            show this help message and exit
  -n RUN_NAME [RUN_NAME ...], --name RUN_NAME [RUN_NAME ...]
                        Names of the analysis runs to show result count
                        breakdown for.
  -a, --all             Show breakdown for all analysis runs.
  -s, --suppressed      Filter results to only show suppressed entries.
                        (default: False)
  --filter FILTER       Filter results. The filter string has the following
                        format:
                        [<SEVERITIES>]:[<CHECKER_NAMES>]:[<FILE_PATHS>] where
                        severites, checker_names, file_paths should be a comma
                        separated list, e.g.:
                        "high,medium:unix,core:*.cpp,*.h" (default: ::)
~~~~~~~~~~~~~~~~~~~~~

### Remove analysis runs (`del`)

~~~~~~~~~~~~~~~~~~~~~
usage: CodeChecker cmd del [-h]
                           (-n RUN_NAME [RUN_NAME ...] |
                            --all-before-run RUN_NAME |
                            --all-after-run RUN_NAME |
                            --all-after-time TIMESTAMP |
                            --all-before-time TIMESTAMP)
                           [--url PRODUCT_URL]
                           [--verbose {info,debug,debug_analyzer}]

Remove analysis runs from the server based on some criteria. NOTE! When a run
is deleted, ALL associated information is permanently lost!

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
~~~~~~~~~~~~~~~~~~~~~

### Manage and export/import suppressions (`suppress`)

~~~~~~~~~~~~~~~~~~~~~
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
~~~~~~~~~~~~~~~~~~~~~

#### Import suppressions between server and suppress file


~~~~~~~~~~~~~~~~~~~~~
  -i SUPPRESS_FILE, --import SUPPRESS_FILE
                        Import suppression from the suppress file into the
                        database.
~~~~~~~~~~~~~~~~~~~~~

`--import` **appends** the suppressions found in the given suppress file to
the database on the server.

### Manage product configuration of a server (`products`)

Please see [Product management](products.md) for details.

### Authenticate to the server (`login`)

~~~~~~~~~~~~~~~~~~~~~
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
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level. (default: info)
~~~~~~~~~~~~~~~~~~~~~

If a server [requires privileged access](authentication.md), you must
log in before you can access the data on the particular server. Once
authenticated, your session is available for some time and `CodeChecker cmd`
can be used normally.

The password can be saved on the disk. If such "preconfigured" password is
not found, the user will be asked, in the command-line, to provide credentials.

# Advanced usage

## Run CodeChecker distributed in a cluster

You may want to configure CodeChecker to do the analysis on separate machines in a distributed way.
Start the postgres database on a central machine (in this example it is called codechecker.central) on a remotely accessible address and port and then run
```CodeChecker check``` on multiple machines (called host1 and host2), specify the remote dbaddress and dbport and use the same run name.

Create and start an empty database to which the CodeChecker server can connect.

## Setup PostgreSQL (one time only)

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
# Start the central CodeChecker server
CodeChecker server -w ~/codechecker_workspace --dbaddress localhost --dbport 5432 --view-port 8001
~~~~~~~~~~~~~~~~~~~~~

## Run CodeChecker on multiple hosts

Then you can run CodeChecker on multiple hosts but using the same run name (in this example this is called "distributed_run".
CodeChecker server is listening on codechecker.central port 8001.

~~~~~~~~~~~~~~~~~~~~~
# On host1 we check module1
CodeChecker check -w /tmp/codechecker_ws -b "cd module_1;make" --port 8001 --host codechecker.central distributed_run

# On host2 we check module2
CodeChecker check -w /tmp/codechecker_ws -b "cd module_2;make" --port 8001 --host codechecker.central disributed_run
~~~~~~~~~~~~~~~~~~~~~

### PostgreSQL authentication (optional)

If a CodeChecker is run with a user that needs database authentication, the
PGPASSFILE environment variable should be set to a pgpass file
For format and further information see PostgreSQL documentation:
http://www.postgresql.org/docs/current/static/libpq-pgpass.html

# Debugging CodeChecker

Command line flag can be used to turn in CodeChecker debug mode. The different
subcommands can be given a `-v` flag which needs a parameter. Possible values
are `debug`, `debug_analyzer` and `info`. Default is `info`.

`debug_analyzer` switches analyzer related logs on:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check <name> -b <build_command> --verbose debug_analyzer
~~~~~~~~~~~~~~~~~~~~~

Turning on CodeChecker debug level logging is possible for the most
subcommands:

~~~~~~~~~~~~~~~~~~~~~
CodeChecker check <name> -b <build_command> --verbose debug
CodeChecker server -v <view_port> --verbose debug
~~~~~~~~~~~~~~~~~~~~~

If debug logging is enabled and PostgreSQL database is used, PostgreSQL logs
are written to `postgresql.log` in the workspace directory.
