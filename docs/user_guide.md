Table of Contents
=================
* [CodeChecker](#codechecker)
    * [Default configuration](#default-configuration)
* [Easy analysis wrappers](#easy-analysis-wrappers)
    * [`check`](#check)
* [`PRODUCT_URL` format](#product-url-format)
    * [Example](#product-url-format-example)
* [Available CodeChecker subcommands](#available-commands)
    * [`log`](#log)
        * [BitBake](#bitbake)
        * [CCache](#ccache)
    * [`analyze`](#analyze)
        * [_Skip_ file](#skip)
            * [Absolute path examples](#skip-abs-example)
            * [Relative or partial path examples](#skip-rel-example)
        * [Analyzer configuration](#analyzer-configuration)
            * [Compiler-specific include path and define detection (cross compilation)](#include-path)
            * [Forwarding compiler options](#forwarding-compiler-options)
              * [_Clang Static Analyzer_](#clang-static-analyzer)
              * [_Clang-Tidy_](#clang-tidy)
        * [Toggling checkers](#toggling-checkers)
            * [Checker profiles](#checker-profiles)
            * [`--enable-all`](#enable-all)
        * [Toggling compiler warnings](#toggling-warnings)
        * [Cross Translation Unit (CTU) analysis mode](#ctu)
        * [Statistical analysis mode](#statistical)
    * [`parse`](#parse)
            * [Exporting source code suppression to suppress file](#suppress-file)
    * [`store`](#store)
        * [Using SQLite for database](#sqlite)
    * [`checkers`](#checkers)
    * [`analyzers`](#analyzers)
    * [`server`](#server)
        * [Creating a public server](#public-server)
        * [Configuring database and server settings' location](#server-settings)
        * [Master superuser and authentication forcing](#auth-force)
        * [Enfore secure socket (SSL)](#ssl)
        * [Managing running servers](#managing-running-servers)
        * [Manage server database upgrades](#manage-server-database-upgrade)
    * [`cmd`](#cmd)
        * [`components` (Source components)](#source-components)
            * [`new` (New/Edit source component)](#new-source-components)
                * Format of [component file](#component-file)
            * [`list` (List source components)](#list-source-components)
            * [`del` (Delete source components)](#delete-source-components)
        * [`runs` (List runs)](#cmd-runs)
        * [`history` (List of run histories)](#cmd-history)
        * [`results` (List analysis results' summary)](#cmd-results)
            * [Example](#cmd-results-example)
        * [`diff` (Show differences between two runs)](#cmd-diff)
          * [Example](#cmd-diff-example)
        * [`sum` (Show summarised count of results)](#cmd-sum)
            * [Example](#cmd-sum-example)
        * [`del` (Remove analysis runs)](#cmd-del)
        * [`suppress` (Manage and export/import suppressions)](#manage-suppressions)
            * [Import suppressions between server and suppress file](#import-suppressions)
        * [`products` (Manage product configuration of a server)](#cmd-product)
        * [`login` (Authenticate to the server)](#cmd-login)
* [Source code comments (review status)](#source-code-comments)
    * [Supported formats](#supported-formats)
* [Advanced usage](#advanced-usage)
    * [Run CodeChecker distributed in a cluster](#distributed-in-cluster)
    * [Setup PostgreSQL (one time only)](#pgsql)
    * [Run CodeChecker on multiple hosts](#multiple-hosts)
        * [PostgreSQL authentication (optional)](#pgsql-auth)
* [Debugging CodeChecker](#debug)

# CodeChecker <a name="codechecker"></a>

First of all, you have to setup the environment for CodeChecker.
CodeChecker uses SQLite database (by default) to store the results
which is also packed into the package.

Running CodeChecker is via its main invocation script, `CodeChecker`:

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
```


## Default configuration <a name="default-configuration"></a>

Used ports:

* `5432` - PostgreSQL
* `8001` - CodeChecker server

The server listens only on the local machine.

The initial product is called `Default`.

# Easy analysis wrappers <a name="easy-analysis-wrappers"></a>

CodeChecker provides, along with the more fine-tuneable commands, some easy
out-of-the-box invocations to ensure the most user-friendly operation, the
**check** mode.

## `check` <a name="check"></a>

It is possible to easily analyse the project for defects without keeping the
temporary analysis files and without using any database to store the reports
in, but instead printing the found issues to the standard output.

To analyse your project by doing a build and reporting every found issue in the
built files, execute

```sh
CodeChecker check --build "make"
```

Please make sure your build command actually compiles (builds) the source
files you intend to analyse, as CodeChecker only analyzes files that had been
used by the build system.

If you have an already existing JSON Compilation Commands file, you can also
supply it to `check`:

```sh
CodeChecker check --logfile ./my-build.json
```

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

```
usage: CodeChecker check [-h] [-o OUTPUT_DIR] [-t {plist}] [-q] [-f]
                         (-b COMMAND | -l LOGFILE) [-j JOBS] [-c]
                         [--report-hash {context-free}] [-i SKIPFILE]
                         [--analyzers ANALYZER [ANALYZER ...]]
                         [--add-compiler-defaults] [--capture-analysis-output]
                         [--saargs CLANGSA_ARGS_CFG_FILE]
                         [--tidyargs TIDY_ARGS_CFG_FILE]
                         [--tidy-config TIDY_CONFIG] [--timeout TIMEOUT]
                         [--ctu | --ctu-collect | --ctu-analyze]
                         [-e checker/group/profile] [-d checker/group/profile]
                         [--enable-all] [--print-steps]
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
  --report-hash {context-free}
  -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
  --analyzers ANALYZER [ANALYZER ...]
  --add-compiler-defaults
  --capture-analysis-output
  --saargs CLANGSA_ARGS_CFG_FILE
  --tidyargs TIDY_ARGS_CFG_FILE
  --tidy-config TIDY_CONFIG
  --timeout TIMEOUT

cross translation unit analysis arguments:
  These arguments are only available if the Clang Static Analyzer supports
  Cross-TU analysis. By default, no CTU analysis is run when 'CodeChecker
  analyze' is called.

  --ctu, --ctu-all
  --ctu-collect
  --ctu-analyze
  --ctu-on-the-fly

statistical analysis arguments:
  This is an EXPERIMENTAL feature.These arguments are only available if the Clang Static Analyzer supports
  Statistical analysis. By default, no Statistical analysis is run when 'CodeChecker
  analyze' is called.

  --stats
  --stats-collect
  --stats-use
  --stats-min-sample-count
  --stats-relevance-threshold

checker configuration:

  -e checker/group/profile, --enable checker/group/profile
  -d checker/group/profile, --disable checker/group/profile

output arguments:
  --print-steps
```

## `PRODUCT_URL` format <a name="product-url-format"></a>

Several subcommands, such as `store` and `cmd` need a connection specification
on which server and for which *Product* (read more [about
products](products.md)) an action, such as report storage or result
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
allocated when the [product is created](products.md), by the server's
administrators. The product must exist and be properly configured before any
normal operation could be done on it.

If no URL is specified, the default value `http://localhost:8001/Default` will
be used: a standard HTTP CodeChecker server running on the local machine, on
the default port, using the *Default* product.

### Example <a name="product-url-format-example"></a>

The URL `https://codechecker.example.org:9999/SampleProduct` will access the
server machine `codechecker.example.org` trying to connect to a server
listening on port `9999` via HTTPS. The product `SampleProduct` will be used.

# Available CodeChecker subcommands <a name="available-commands"></a>

## `log` <a name="log"></a>

The first step in performing an analysis on your project is to record
information about the files in your project for the analyzers. This is done by
recording a build of your project, which is done by the command `CodeChecker
log`.

```
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
                        Set verbosity level.
```

Please note, that only the files that are used in the given `--build` argument
will be recorded. To analyze your whole project, make sure your build tree has
been cleaned before executing `log`.

You can change the compilers that should be logged.
Set `CC_LOGGER_GCC_LIKE` environment variable to a colon separated list.
For example (default):

```sh
export CC_LOGGER_GCC_LIKE="gcc:g++:clang"
```

Example:

```sh
CodeChecker log -o ../codechecker_myProject_build.log -b "make -j2"
```

### BitBake
Do the following steps to log compiler calls made by
[BitBake](https://github.com/openembedded/bitbake) using CodeChecker.

* Add `LD_LIBRARY_PATH`, `LD_PRELOAD`, `CC_LOGGER_GCC_LIKE` and `CC_LOGGER_FILE`
to `BB_ENV_EXTRAWHITE` variable in your shell environment:
```bash
export BB_ENV_EXTRAWHITE="LD_PRELOAD LD_LIBRARY_PATH CC_LOGGER_FILE CC_LOGGER_GCC_LIKE $BB_ENV_EXTRAWHITE"
```
 **Note:** `BB_ENV_EXTRAWHITE` specifies an additional set of variables to allow through
(whitelist) from the external environment into BitBake's datastore.

* Add the following lines to the `conf/bitbake.conf` file:
```bash
export LD_PRELOAD
export LD_LIBRARY_PATH
export CC_LOGGER_FILE
export CC_LOGGER_GCC_LIKE
```

* Run `CodeChecker log`:
```bash
CodeChecker log -o ../compile_commands.json -b "bitbake myProject"
```

### CCache
If your build system setup uses CCache then it can be logged too. If
`CC_LOGGER_GCC_LIKE` contains "cc" or "ccache" directly then these actions will
also be logged. Depending on CCache configuration there are two forms how it
can be used:
```bash
ccache g++ -DHELLO=world main.cpp
ccache -DHELLO=world main.cpp
```
The compiler may or may not follow `ccache` command. If the compiler is missing
then the used compiler can be configured in a config file or an environment
variable.

Currently CodeChecker supports only the first case where the compiler name is
also included in the build command.

## `analyze` <a name="analyze"></a>

After a JSON Compilation Command Database has been created, the next step is
to invoke and execute the analyzers. CodeChecker will use the specified
`logfile`s (there can be multiple given) and create the outputs to the
`--output` directory. (These outputs will be `plist` files, currently only
these are supported.) The machine-readable output files can be used later on
for printing an overview in the terminal (`CodeChecker parse`) or storing
(`CodeChecker store`) analysis results in a database, which can later on be
viewed in a browser.

Example:

```sh
CodeChecker analyze ../codechecker_myProject_build.log -o my_plists
```

`CodeChecker analyze` supports a myriad of fine-tuning arguments, explained
below:

```
usage: CodeChecker analyze [-h] [-j JOBS] [-i SKIPFILE] -o OUTPUT_PATH
                           [--compiler-info-file COMPILER_INFO_FILE]
                           [-t {plist}] [-q] [-c]
                           [--report-hash {context-free}] [-n NAME]
                           [--analyzers ANALYZER [ANALYZER ...]]
                           [--add-compiler-defaults]
                           [--capture-analysis-output]
                           [--saargs CLANGSA_ARGS_CFG_FILE]
                           [--tidyargs TIDY_ARGS_CFG_FILE]
                           [--tidy-config TIDY_CONFIG] [--timeout TIMEOUT]
                           [--ctu | --ctu-collect | --ctu-analyze]
                           [--ctu-reanalyze-on-failure]
                           [-e checker/group/profile]
                           [-d checker/group/profile] [--enable-all]
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
  --compiler-info-file COMPILER_INFO_FILE
                        Read the compiler includes and target from the
                        specified file rather than invoke the compiler
                        executable.
  -t {plist}, --type {plist}, --output-format {plist}
                        Specify the format the analysis results should use.
                        (default: plist)
  -q, --quiet           Do not print the output or error of the analyzers to
                        the standard output of CodeChecker.
  -c, --clean           Delete analysis reports stored in the output
                        directory. (By default, CodeChecker would keep reports
                        and overwrites only those files that were update by
                        the current build command).
 --report-hash {context-free}
                        EXPERIMENTAL feature. Specify the hash calculation
                        method for reports. If this option is not set, the
                        default calculation method for Clang Static Analyzer
                        will be context sensitive and for Clang Tidy it will
                        be context insensitive. If this option is set to
                        'context-free' bugs will be identified with the
                        CodeChecker generated context free hash for every
                        analyzers. USE WISELY AND AT YOUR OWN RISK!
  -n NAME, --name NAME  Annotate the run analysis with a custom name in the
                        created metadata file.
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.
```

### _Skip_ file <a name="skip"></a>

```
-i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                      Path to the Skipfile dictating which project files
                      should be omitted from analysis.
```

Skipfiles filter which files should or should not be analyzed. CodeChecker
reads the skipfile from **top to bottom and stops at the first matching pattern**
when deciding whether or not a file should be analyzed.

Each line in the skip file begins with a `-` or a `+`, followed by a path glob
pattern. `-` means that if a file matches a pattern it should **not** be
checked, `+` means that it should be.

 * Absolute directory paths should start with `/`.
 * Relative directory paths should start with `*`.
 * Path parts should start and end with `*`.
 * To skip everything use the `-*` mark. **Watch out for the order!**

#### Absolute path examples <a name="skip-abs-example"></a>

```
-/skip/all/files/in/directory/*
-/do/not/check/this.file
+/dir/do.check.this.file
-/dir/*
```

In the above example, every file under `/dir` **will be** skipped, except the
one explicitly specified to **be analyzed** (`/dir/do.check.this.file`).

#### Relative or partial path examples <a name="skip-rel-example"></a>

```
+*/my_project/my_lib_to_skip/important_file.cpp
-*/my_project/my_lib_to_skip*
-*/my_project/3pplib/*
+*/my_project/*
```

In the above example, `important_file.cpp` will be analyzed even if every file
where the path matches to `/my_project/my_lib_to_skip` will be skiped.  
Every other file where the path contains `/myproject` except the files in the 
`my_project/3pplib` will be analyzed.

The provided *shell-style* pattern is converted to a regex with the [fnmatch.translate](https://docs.python.org/2/library/fnmatch.html#fnmatch.translate).

### Analyzer configuration <a name="analyzer-configuration"></a>

```
analyzer arguments:
  --analyzers ANALYZER [ANALYZER ...]
                        Run analysis only with the analyzers specified.
                        Currently supported analyzers are: clangsa, clang-
                        tidy.
  --add-compiler-defaults
                        DEPRECATED. Always True. 
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
  --tidy-config TIDY_CONFIG
                        A file in YAML format containing the configuration of
                        clang-tidy checkers. The file can be dumped by
                        'CodeChecker analyzers --dump-config clang-tidy'
                        command.
  --timeout TIMEOUT     The amount of time (in seconds) that each analyzer can
                        spend, individually, to analyze the project. If the
                        analysis of a particular file takes longer than this
                        time, the analyzer is killed and the analysis is
                        considered as a failed one.
```

CodeChecker supports several analyzer tools. Currently, these analyzers are
the [_Clang Static Analyzer_](http://clang-analyzer.llvm.org) and
[_Clang-Tidy_](http://clang.llvm.org/extra/clang-tidy). `--analyzers` can be
used to specify which analyzer tool should be used (by default, all supported
are used). The tools are completely independent, so either can be omitted if
not present as they are provided by different binaries.

See [Configure Clang Static Analyzer and checkers](checker_and_analyzer_configuration.md) documentation for
a more detailed description how to use the `saargs` and `tidyargs` arguments.


#### Compiler-specific include path and define detection (cross compilation) <a name="include-path"></a>

Some of the include paths are hardcoded during compiler build. If a (cross)
compiler is used to build a project it is possible that the wrong include
paths are searched and the wrong headers will be included which causes
analyses to fail. These hardcoded include paths and defines can be marked for
automatically detection by specifying the `--add-compiler-defaults` flag.

CodeChecker will get the hardcoded values for the compilers set in the
`CC_LOGGER_GCC_LIKE` environment variable.

```sh
export CC_LOGGER_GCC_LIKE="gcc:g++:clang"
```

If there are still compilation errors after using the `--add-compiler-defaults`
argument, it is possible that the wrong build target architecture
(32bit, 64bit) is used. Please try to forward these compilation flags
to the analyzers:

 - `-m32` (32-bit build)
 - `-m64` (64-bit build)

#### Forwarding compiler options <a name="forwarding-compiler-options"></a>

Forwarded options can modify the compilation actions logged by the build logger
or created by CMake (when exporting compile commands). The extra compiler
options can be given in config files which are provided by the flags
described below.

The config files can contain placeholders in `$(ENV_VAR)` format. If the
`ENV_VAR` environment variable is set then the placeholder is replaced to its
value. Otherwise an error message is logged saying that the variable is not
set, and in this case an empty string is inserted in the place of the
placeholder.

##### <a name="clang-static-analyzer"></a> _Clang Static Analyzer_

Use the `--saargs` argument to a file which contains compilation options.

```sh
CodeChecker analyze mylogfile.json --saargs extra_sa_compile_flags.txt -n myProject
```

Where the `extra_sa_compile_flags.txt` file contains additional compilation
options, for example:

```sh
-I~/include/for/analysis -I$(MY_LIB)/include -DDEBUG
```

(where `MY_LIB` is the path of a library code)

##### _Clang-Tidy_ <a name="clang-tidy"></a>

Use the `--tidyargs` argument to a file which contains compilation options.

```sh
CodeChecker analyze mylogfile.json --tidyargs extra_tidy_compile_flags.txt -n myProject
```

Where the `extra_tidy_compile_flags.txt` file contains additional compilation
flags.

Clang-Tidy requires a different format to add compilation options.
Compilation options can be added before (`-extra-arg-before=<string>`) and
after (`-extra-arg=<string>`) the original compilation options.

Example:

```sh
-extra-arg-before='-I~/include/for/analysis' -extra-arg-before='-I~/other/include/for/analysis/' -extra-arg-before='-I$(MY_LIB)/include' -extra-arg='-DDEBUG'
```

(where `MY_LIB` is the path of a library code)

### Toggling checkers <a name="toggling-checkers"></a>

The list of checkers to be used in the analysis can be fine-tuned with the
`--enable` and `--disable` options. See `codechecker-checkers` for the list of
available checkers in the binaries installed on your system.

```
checker configuration:

  -e checker/group/profile, --enable checker/group/profile
                        Set a checker (or checker group or checker profile)
                        to BE USED in the analysis.
  -d checker/group/profile, --disable checker/group/profile
                        Set a checker (or checker group or checker profile)
                        to BE PROHIBITED from use in the analysis.
  --enable-all          Force the running analyzers to use almost every
                        checker available. The checker groups 'alpha.',
                        'debug.' and 'osx.' (on Linux) are NOT enabled
                        automatically and must be EXPLICITLY specified.
                        WARNING! Enabling all checkers might result in the
                        analysis losing precision and stability, and could
                        even result in a total failure of the analysis. USE
                        WISELY AND AT YOUR OWN RISK!
```

Both `--enable` and `--disable` take individual checkers, checker groups or
checker profiles as their argument and there can be any number of such flags
specified. Flag order is important, subsequent options **overwrite** previously
specified ones. For example

```sh
--enable extreme --disable core.uninitialized --enable core.uninitialized.Assign
```

will enable every checker of the `extreme` profile that do not belong to the
 `core.uninitialized` group, with the exception of `core.uninitialized.Assign`,
which will be enabled after all.

Disabling certain checkers - such as the `core` group - is unsupported by
the LLVM/Clang community, and thus discouraged.

### Toggling compiler warnings <a name="toggling-warnings"></a>
Compiler warnings are diagnostic messages that report constructions that are
not inherently erroneous but that are risky or suggest there may have been an
error. Compiler warnings are named `clang-diagnostic-<warning-option>`, e.g.
Clang warning controlled by `-Wliteral-conversion` will be reported with check
name `clang-diagnostic-literal-conversion`.
You can fine-tune which warnings to use in the analysis by setting the enabled
and disabled flags starting from the bigger groups and going inwards. For
example

```sh
--enable Wunused --disable Wno-unused-parameter
```
or
```sh
--enable Wunused --disable Wunused-parameter
```
will enable every `unused` warnings except `unused-parameter`. These flags
should start with a capital `W` or `Wno-` prefix followed by the warning name
(E.g.: `-e Wliteral-conversion`, `-d Wno-literal-conversion` or
`-d Wliteral-conversion`). To turn off a compiler warning you can use the
negative form beginning with `Wno-` (e.g.: `--disable Wno-literal-conversion`)
or you can use the positive form beginning with `W` (e.g.:
`--enable Wliteral-conversion`). For more information see:
https://clang.llvm.org/docs/DiagnosticsReference.html.

**Note**: by default `-Wall` and `-Wextra` warnings are enabled.


#### Checker profiles <a name="checker-profiles"></a>

Checker profiles describe custom sets of enabled checks which can be specified
in the `{INSTALL_DIR}/config/config.json` file. Three built-in options are
available grouping checkers by their quality (measured by their false positive
rate): `default`, `sensitive` and `extreme`. In addition, profile `portability`
contains checkers for detecting platform-dependent code issues. These issues
can arise when migrating code from 32-bit to 64-bit architectures, and the root
causes of the bugs tend to be overflows, sign extensions and widening
conversions or casts. Detailed information about profiles can be retrieved by
the `CodeChecker checkers` command.

Note: `list` is a reserved keyword used to show all the available profiles and
thus should not be used as a profile name. Profile names should also be
different from checker(-group) names as they are enabled using the same syntax
and coinciding names could cause unintended behavior.


#### `--enable-all` <a name="enable-all"></a>

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

```sh
--enable-all --enable alpha --disable misc
```

can be used to "further" enable `alpha.` checkers, and disable `misc` ones.

### Cross Translation Unit (CTU) analysis mode <a name="ctu"></a>

If the `clang` static analyzer binary in your installation supports
[Cross Translation Unit analysis](http://llvm.org/devmtg/2017-03//2017/02/20/accepted-sessions.html#7),
CodeChecker can execute the analyzers with this mode enabled.

These options are only visible in `analyze` if CTU support is present. CTU
mode uses some extra storage space under the specified `--output-dir`.

```
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
```

### Statistical analysis mode <a name="statistical"></a>

If the `clang` static analyzer binary in your installation supports
statistical checkers CodeChecker can execute the analyzers
with this mode enabled.

These options are only visible in `analyze` if the experimental
statistical analysis support is present.

```
EXPERIMENTAL statistics analysis feature arguments:
  These arguments are only available if the Clang Static Analyzer supports
  Statistics-based analysis (e.g. statisticsCollector.ReturnValueCheck,
  statisticsCollector.SpecialReturnValue checkers are available).

  --stats-collect STATS_OUTPUT, --stats-collect STATS_OUTPUT
                        EXPERIMENTAL feature. Perform the first, 'collect'
                        phase of Statistical analysis. This phase generates
                        extra files needed by statistics analysis, and puts
                        them into '<STATS_OUTPUT>'. NOTE: If this argument is
                        present, CodeChecker will NOT execute the analyzers!
  --stats-use STATS_DIR, --stats-use STATS_DIR
                        EXPERIMENTAL feature. Use the previously generated
                        statistics results for the analysis from the given
                        '<STATS_DIR>'.
  --stats               EXPERIMENTAL feature. Perform both phases of
                        Statistical analysis. This phase generates extra files
                        needed by statistics analysis and enables the
                        statistical checkers. No need to enable them
                        explicitly.
 --stats-min-sample-count STATS_MIN_SAMPLE_COUNT, --stats-min-sample-count STATS_MIN_SAMPLE_COUNT
                        EXPERIMENTAL feature. Minimum number of samples
                        (function call occurrences) to be collected for a
                        statistics to be relevant.(default: 10)
  --stats-relevance-threshold STATS_RELEVANCE_THRESHOLD, --stats-relevance-threshold STATS_RELEVANCE_THRESHOLD
                        EXPERIMENTAL feature. The minimum ratio of
                        calls of function f that must have a certain property
                        to consider it true for that function (calculated as calls 
                        with a property/all calls). CodeChecker will warn for calls 
                        of f that do not have that property.(default: 0.85)
 
```

## `parse` <a name="parse"></a>

`parse` is used to read previously created machine-readable analysis results
(such as `plist` files), usually previously generated by `CodeChecker analyze`.
`parse` prints analysis results to the standard output.

```
usage: CodeChecker parse [-h] [-t {plist}] [--export {html}]
                         [-o OUTPUT_PATH] [-c] [--suppress SUPPRESS]
                         [--export-source-suppress] [--print-steps]
                         [--verbose {info,debug,debug_analyzer}]
                         file/folder [file/folder ...]

Parse and pretty-print the summary and results from one or more 'codechecker-
analyze' result files. Bugs which are commented by using "false_positive",
"suppress" and "intentional" source code comments will not be printed by the
`parse` command.

positional arguments:
  file/folder           The analysis result files and/or folders containing
                        analysis results which should be parsed and printed.

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
  -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                        Path to the Skipfile dictating which project files
                        should be omitted from analysis. Please consult the
                        User guide on how a Skipfile should be laid out.
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.

export arguments:
  -e {html}, --export {html}
                        Specify extra output format type. (default: None)
  -o OUTPUT_PATH, --output OUTPUT_PATH
                        Store the output in the given folder. (default: None)
  -c, --clean           DEPRECATED. Delete output results stored in the output
                        directory. (By default, it would keep output files and
                        overwrites only those that belongs to a plist file
                        given by the input argument. (default: True)
```

For example, if the analysis was run like:

```sh
CodeChecker analyze ../codechecker_myProject_build.log -o my_plists
```

then the results of the analysis can be printed with

```sh
CodeChecker parse ./my_plists
```

## `store` <a name="store"></a>

A `Codechecker server` needs to be started before the reports can be stored to
a database.

`store` is used to save previously created machine-readable analysis results
(such as `plist` files), usually previously generated by `CodeChecker analyze`
to the database.

```
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
  --trim-path-prefix [TRIM_PATH_PREFIX [TRIM_PATH_PREFIX ...]]
                        Removes leading path from files which will be stored.
                        So if you have /a/b/c/x.cpp and /a/b/c/y.cpp then by
                        removing "/a/b/" prefix will store files like c/x.cpp
                        and c/y.cpp. If multiple prefix is given, the longest
                        match will be removed.
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


The results can be viewed by connecting to such a server in a Web browser or
via 'CodeChecker cmd'.
```

For example, if the analysis was run like:

```sh
CodeChecker analyze ../codechecker_myProject_build.log -o ./my_plists
```

then the results of the analysis can be stored with this command:

```sh
CodeChecker store ./my_plists -n my_project
```

### Using SQLite for database <a name="sqlite"></a>

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

## `checkers`<a name="checkers"></a>

List the checkers available in the installed analyzers which can be used when
performing an analysis.

By default, `CodeChecker checkers` will list all checkers, one per each row,
providing a quick overview on which checkers are available in the analyzers.

```
usage: CodeChecker checkers [-h] [--analyzers ANALYZER [ANALYZER ...]]
                            [--details] [--profile {PROFILE/list}]
                            [--only-enabled | --only-disabled]
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
  --profile {PROFILE/list}
                        List checkers enabled by the selected profile.
                        'list' is a special option showing details about
                        profiles collectively.
  --only-enabled        Show only the enabled checkers.
  --only-disabled       Show only the disabled checkers.
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        The format to list the applicable checkers as.
                        (default: rows)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.
```

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

## <a name="analyzers"></a> 6. `analyzers` mode

List the available and supported analyzers installed on the system. This command
can be used to retrieve the to-be-used analyzers' install path and version
information.

By default, this command only lists the names of the available analyzers (with
respect to the environment CodeChecker is run in).

```
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
  --dump-config {clangsa,clang-tidy}
                        Dump the available checker options for the given
                        analyzer to the standard output. Currently only clang-
                        tidy supports this option. The output can be
                        redirected to a file named .clang-tidy. If this file
                        is placed to the project directory then the options
                        are applied to the files under that directory. This
                        config file can also be provided via 'CodeChecker
                        analyze' and 'CodeChecker check' commands.
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        Specify the format of the output list. (default: rows)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.
```

A detailed view of the available analyzers is available via `--details`. In the
*detailed view*, version string and install path is also printed.

A machine-readable `csv` or `json` output can be generated by supplying the
`--output csv` or `--output json` argument.

## `server` <a name="server"></a>

To view and store the analysis reports in a database, a `CodeChecker server`
must be started. This is done via the `server` command, which creates a
standard Web server and initializes or connects to a database with
the given configuration.

The CodeChecker Viewer server can be browsed by a Web browser by opening the
address of it (by default, [`http://localhost:8001`](http://localhost:8001)),
or via the `CodeChecker cmd` command-line client.

```
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
  --skip-db-cleanup     Skip performing cleanup jobs on the database like
                        removing unused files.
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

To start a server with default configuration, simply execute

```sh
CodeChecker server
```

### Creating a public server <a name="public-server"></a>

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

### Configuring database and server settings location  <a name="server-settings"></a>

The `--sqlite` (or `--postgresql` and the various `--db-` arguments) can be
used to specify where the database, containing the analysis reports is.

`--config-directory` specifies where the server configuration files, such as
[authentication config](authentication.md) is. For example, one can start
two servers with two different product layout, but with the same authorisation
configuration:

```sh
CodeChecker server --sqlite ~/major_bugs.sqlite -f ~/.codechecker -p 8001
CodeChecker server --sqlite ~/minor_bugs.sqlite -f ~/.codechecker -p 8002
```

The `--workspace` argument can be used to _shortcut_ this specification: by
default, the configuration directory is the _workspace_ itself, and therein
resides the `config.sqlite` file, containing the product configuration.

If the server is started in `--sqlite` mode and fresh, that is, no product
configuration file is found, a product named `Default`, using `Default.sqlite`
in the configuration directory is automatically created. Please see
[Product management](products.md) for details on how to configure products.

### Master superuser and authentication forcing <a name="auth-force"></a>

```
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
```

### Enfore secure socket (SSL) <a name="ssl"></a>

You can enforce SSL security on your listening socket. In this case all clients must
access your server using the `https://host:port` URL format.

To enable SSL simply place an SSL certificate to `<CONFIG_DIRECTORY>/cert.pem`
and the corresponding private key to `<CONFIG_DIRECTORY>/key.pem`.
You can generate these certificates for example 
using the [openssl tool](https://www.openssl.org/).
When the server finds these files upon start-up, 
SSL will be automatically enabled. 

### Managing running servers <a name="managing-running-servers"></a>

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

### Manage server database upgrades <a name="manage-server-database-upgrade"></a>

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


## `cmd` <a name="cmd"></a>

The `CodeChecker cmd` is a lightweight command line client that can be used to
view analysis results from the command-line. The command-line client can also
be integrated into a continuous integration loop or can be used to schedule
maintenance tasks.

Most of the features available in a Web browser opening the analysis result
viewer server on its port is available in the `cmd` tool.

```
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
```

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
                        Filter results by review statuses. This can be used
                        only if basename or newname is a run name (on the
                        remote server). (default: ['unreviewed', 'confirmed'])
  --detection-status [DETECTION_STATUS [DETECTION_STATUS ...]]
                        Filter results by detection statuses. This can be used
                        only if basename or newname is a run name (on the
                        remote server). (default: ['new', 'reopened',
                        'unresolved'])
  --severity [SEVERITY [SEVERITY ...]]
                        Filter results by severities.
  --tag [TAG [TAG ...]]
                        Filter results by version tag names. This can be used
                        only if basename or newname is a run name (on the
                        remote server).
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
  --component [COMPONENT [COMPONENT ...]]
                        Filter results by source components. This can be used
                        only if basename or newname is a run name (on the
                        remote server).
  --detected-at TIMESTAMP
                        Filter results by detection date. The format of
                        TIMESTAMP is 'year:month:day:hour:minute:second' (the
                        "time" part can be omitted, in which case midnight
                        (00:00:00) is used).
  --fixed-at TIMESTAMP  Filter results by fix date. The format of TIMESTAMP is
                        'year:month:day:hour:minute:second' (the "time" part
                        can be omitted, in which case midnight (00:00:00) is
                        used).
  -s, --suppressed      DEPRECATED. Use the '--filter' option to get false
                        positive (suppressed) results. Show only suppressed
                        results instead of only unsuppressed ones.
  --filter FILTER       DEPRECATED. Filter results. Use separated filter
                        options to filter the results. The filter string has
                        the following format: [<SEVERITIES>]:[<CHECKER_NAMES>]
                        :[<FILE_PATHS>]:[<DETECTION_STATUSES>]:[<REVIEW_STATUS
                        ES>] where severites, checker_names, file_paths,
                        detection_statuses, review_statuses should be a comma
                        separated list, e.g.: "high,medium:unix,core:*.cpp,*.h
                        :new,unresolved:false_positive,intentional"
```

### Source components (`components`) <a name="source-components"></a>

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


#### New/Edit source component <a name="new-source-components"></a>

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

##### Format of component file <a name="component-file"></a>

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

#### List source components <a name="list-source-components"></a>
List the name and basic information about source component added to the
server.
```
usage: CodeChecker cmd components list [-h] [--url PRODUCT_URL]
                                       [-o {plaintext,rows,table,csv,json}]
                                       [--verbose {info,debug,debug_analyzer}]

List the name and basic information about source component added to the
server.
```

#### Delete source components <a name="delete-source-components"></a>

```
usage: CodeChecker cmd components del [-h] [--url PRODUCT_URL]
                                      [--verbose {info,debug,debug_analyzer}]
                                      NAME

Removes the specified source component.

positional arguments:
  NAME                  The source component name which will be removed.
```

### List runs (`runs`) <a name="cmd-runs"></a>

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
```

### List of run histories (`history`) <a name="cmd-history"></a>

With this command you can list out the specific storage events which happened
during storage processes under multiple run names.

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

### List analysis results' summary (`results`) <a name="cmd-results"></a>

Prints basic information about analysis results, such as location, checker
name, summary.

```
usage: CodeChecker cmd results [-h] [--uniqueing {on,off}]
                               [--report-hash [REPORT_HASH [REPORT_HASH ...]]]
                               [--review-status [REVIEW_STATUS [REVIEW_STATUS ...]]]
                               [--detection-status [DETECTION_STATUS [DETECTION_STATUS ...]]]
                               [--severity [SEVERITY [SEVERITY ...]]]
                               [--tag [TAG [TAG ...]]]
                               [--file [FILE_PATH [FILE_PATH ...]]]
                               [--checker-name [CHECKER_NAME [CHECKER_NAME ...]]]
                               [--checker-msg [CHECKER_MSG [CHECKER_MSG ...]]]
                               [--component [COMPONENT [COMPONENT ...]]]
                               [--detected-at TIMESTAMP]
                               [--fixed-at TIMESTAMP] [-s] [--filter FILTER]
                               [--url PRODUCT_URL]
                               [-o {plaintext,rows,table,csv,json}]
                               [--verbose {info,debug,debug_analyzer}]
                               RUN_NAMES

Show the individual analysis reports' summary.

positional arguments:
  RUN_NAME              Names of the analysis runs to show result summaries of.
                        This has the following format:
                        <run_name_1>:<run_name_2>:<run_name_3> where run names
                        can contain * quantifiers which matches any number of
                        characters (zero or more). So if you have
                        run_1_a_name, run_2_b_name, run_2_c_name, run_3_d_name
                        then "run_2*:run_3_d_name" selects the last three runs.
                        Use 'CodeChecker cmd runs' to get the available runs.

optional arguments:
  -h, --help            show this help message and exit
```

#### Example <a name="cmd-results-example"></a>
```
#Get analysis results for a run:
CodeChecker cmd results my_run

# Get analysis results for multiple runs:
CodeChecker cmd results "my_run1:my_run2"

# Get analysis results by using regex:
CodeChecker cmd results "my_run*"

# Get analysis results for a run and filter the analysis results:
CodeChecker cmd results my_run --severity critical high medium \
    --file "/home/username/my_project/*"
```

### Show differences between two runs (`diff`) <a name="cmd-diff"></a>

This mode shows analysis results (in the same format as `results`) does, but
from the comparison of two runs.

```
usage: CodeChecker cmd diff [-h] -b BASE_RUN -n NEW_RUN [--uniqueing {on,off}]
                            [--report-hash [REPORT_HASH [REPORT_HASH ...]]]
                            [--review-status [REVIEW_STATUS [REVIEW_STATUS ...]]]
                            [--detection-status [DETECTION_STATUS [DETECTION_STATUS ...]]]
                            [--severity [SEVERITY [SEVERITY ...]]]
                            [--tag [TAG [TAG ...]]]
                            [--file [FILE_PATH [FILE_PATH ...]]]
                            [--checker-name [CHECKER_NAME [CHECKER_NAME ...]]]
                            [--checker-msg [CHECKER_MSG [CHECKER_MSG ...]]]
                            [--component [COMPONENT [COMPONENT ...]]]
                            [--detected-at TIMESTAMP] [--fixed-at TIMESTAMP]
                            [-s] [--filter FILTER]
                            (--new | --resolved | --unresolved)
                            [--url PRODUCT_URL]
                            [-o {plaintext,rows,table,csv,json,html}]
                            [-e EXPORT_DIR] [-c]
                            [--verbose {info,debug,debug_analyzer}]

Compare two analysis runs to show the results that differ between the two.

optional arguments:
  -h, --help            show this help message and exit
  -b BASE_RUN, --basename BASE_RUN
                        The 'base' (left) side of the difference: this
                        analysis run is used as the initial state in the
                        comparison. The basename can contain * quantifiers
                        which matches any number of characters (zero or more).
                        So if you have run-a-1, run-a-2 and run-b-1 then
                        "run-a*" selects the first two.
  -n NEW_RUN, --newname NEW_RUN
                        The 'new' (right) side of the difference: this
                        analysis run is compared to the -b/--basename run. The
                        parameter can be a run name(on the remote server) or a
                        local report directory (result of the analyze
                        command). In case of run name the newname can contain
                        * quantifiers which matches any number of characters
                        (zero or more). So if you have run-a-1, run-a-2 and
                        run-b-1 then "run-a*" selects the first two.

comparison modes:
  --new                 Show results that didn't exist in the 'base' but
                        appear in the 'new' run.
  --resolved            Show results that existed in the 'base' but
                        disappeared from the 'new' run.
  --unresolved          Show results that appear in both the 'base' and the
                        'new' run.
```

The command can be used in *local* or *remote* compare modes.

In *local mode* the results of a local analysis (see `CodeChecker analyze`)
can be compared to the results stored (see `CodeChecker store`) on a remote
CodeChecker server or two local report directories can be compared:

- Compare a local analysis directory and a remote run:
  ```sh
  CodeChecker cmd diff -p 8001 --basename my_project --newname ./my_updated_plists --new
  ```
- Compare two local analysis directories:
  ```sh
  CodeChecker cmd diff --basename ./my_updated_plists_base --newname ./my_updated_plists_new --new
  ```

In *remote* compare mode, two runs stored on a remote CodeChecker server can
be compared to each other:

```sh
CodeChecker cmd diff -p 8001 --basename my_project --newname my_new_checkin --new
```

**Note**: unique report identifiers are used to compare analysis results. For
more information see [analyzer report identification](report_identification.md)
documentation.

#### Example <a name="cmd-diff-example"></a>
Let's assume you have the following C++ code:
```cpp
int foo(int z)
{
  if (z == 0)
    return 1 / z; // Division by zero

  return 0;
}

int bar(int x)
{
  int y;
  y = x % 2; // deadcode.DeadStores

  return x % 2;
}
```
If you log (`CodeChecker log -o compile_command.json -b "g++ example.cpp"`),
analyze (`CodeChecker analyze -o ./test_report_dir compile_command.json`) and
parse (`CodeChecker parse ./test_report_dir`) this code with CodeChecker you
will get a `Division by zero` warning in the `foo` function and a
`deadcode.DeadStores` warning in the `bar` function.

Let's store it to a running CodeChecker server with run name `test_run_name`
(`CodeChecker store -n test_run_name ./test_report_dir`).

Now let's fix one of the previous warning in the `foo` function and create a
new function which contains a new warning:
```cpp
int foo(int z)
{
  if (z != 0)
    return 1 / z;

  return 0;
}

int bar(int x)
{
  int y;
  y = x % 2; // deadcode.DeadStores

  return x % 2;
}

void baz(int *p)
{
  if (!p)
    *p = 0; // core.NullDereference
}
```
Analyze the above code again with CodeChecker to the same report
directory (`CodeChecker analyze -o ./test_report_dir compile_command.json`).
If you parse the results (`CodeChecker parse ./test_report_dir`) you will get
a `deadcode.DeadStores` warning in the `bar` function and a
`core.NullDereference` warning in the `baz` function but the previous warning
in the `foo` function will be disappeared because we fixed it.

Now let's compare our local report directory (`test_report_dir`)
to the results stored on a remote CodeChecker server previously
(`test_run_name`). We have 3 options:
  - Show results that didn't exist in the remote run but appear in the local
  report directory (`new`):
  `CodeChecker cmd diff --basename test_run_name --newname ./test_report_dir --new`

  ```
  [HIGH] example.cpp:20:8: Dereference of null pointer (loaded from variable 'p') [core.NullDereference]
    *p = 0; // core.NullDereference
  ```
  - Show results that existed in the remote run but disappeared from the local
  report directory run (`resolved`):
  `CodeChecker cmd diff --basename test_run_name --newname ./test_report_dir --resolved`

  ```
  [HIGH] example.cpp:4:14: Division by zero [core.DivideZero]
    return 1 / z; // Division by zero
  ```
  - Show results that appear in both the remote run and the local report
  directory too (`unresolved`):
  `CodeChecker cmd diff --basename test_run_name --newname ./test_report_dir --unresolved`

  ```
  [LOW] example.cpp:12:3: Value stored to 'y' is never read [deadcode.DeadStores]
    y = x % 2; // deadcode.DeadStores
  ```

### Show summarised count of results (`sum`) <a name="cmd-sum"></a>

```
usage: CodeChecker cmd sum [-h] (-n RUN_NAME [RUN_NAME ...] | -a)
                           [--disable-unique] [--uniqueing {on,off}]
                           [--report-hash [REPORT_HASH [REPORT_HASH ...]]]
                           [--review-status [REVIEW_STATUS [REVIEW_STATUS ...]]]
                           [--detection-status [DETECTION_STATUS [DETECTION_STATUS ...]]]
                           [--severity [SEVERITY [SEVERITY ...]]]
                           [--tag [TAG [TAG ...]]]
                           [--file [FILE_PATH [FILE_PATH ...]]]
                           [--checker-name [CHECKER_NAME [CHECKER_NAME ...]]]
                           [--checker-msg [CHECKER_MSG [CHECKER_MSG ...]]]
                           [--component [COMPONENT [COMPONENT ...]]]
                           [--detected-at TIMESTAMP] [--fixed-at TIMESTAMP]
                           [-s] [--filter FILTER] [--url PRODUCT_URL]
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
  --disable-unique      DEPRECATED. Use the '--uniqueing' option to get
                        uniqueing results. List all bugs even if these end up
                        in the same bug location, but reached through
                        different paths. By uniqueing the bugs a report will
                        be appeared only once even if it is found on several
                        paths.
```

#### Example <a name="cmd-sum-example"></a>
```sh
# Get statistics for a run:
CodeChecker cmd sum -n my_run

# Get statistics for all runs filtered by multiple checker names:
CodeChecker cmd sum --all --checker-name "core.*" "deadcode.*"

# Get statistics for all runs and only for severity 'high':
CodeChecker cmd sum --all --severity "high"
```

### Remove analysis runs (`del`) <a name="cmd-del"></a>

```
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
```

### Manage and export/import suppressions (`suppress`) <a name="manage-suppressions"></a>

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

#### Import suppressions between server and suppress file <a name="import-suppressions"></a>


```
  -i SUPPRESS_FILE, --import SUPPRESS_FILE
                        Import suppression from the suppress file into the
                        database.
```

`--import` **appends** the suppressions found in the given suppress file to
the database on the server.

### Manage product configuration of a server (`products`) <a name="cmd-product"></a>

Please see [Product management](products.md) for details.

### Authenticate to the server (`login`) <a name="cmd-login"></a>

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
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.
```

If a server [requires privileged access](authentication.md), you must
log in before you can access the data on the particular server. Once
authenticated, your session is available for some time and `CodeChecker cmd`
can be used normally.

The password can be saved on the disk. If such "preconfigured" password is
not found, the user will be asked, in the command-line, to provide credentials.


# Source code comments for review status <a name="source-code-comments"></a>

Source code comments can be used in the source files to change the review status
of a specific or all checker results found in a particular line of code.
Source code comment should be above the line where the defect was found, and __no__
empty lines are allowed between the line with the bug and the source code
comment.

Comment lines staring with `//` or C style `/**/` comments are supported.
Watch out for the comment format!

## Supported formats <a name="supported-formats"></a>
The source code comment has the following format:
```sh
// codechecker comment type [checker name] comment
```

Multiple source code comment types are allowed:
 * `codechecker_suppress`
 * `codechecker_false_positive`
 * `codechecker_intentional`
 * `codechecker_confirmed`

Source code comment change the `review status` of a bug in the following form:
 * `codechecker_suppress` and `codechecker_false_positive` to `False positive`
 * `codechecker_intentional` to `Intentional`
 * `codechecker_confirmed` to `Confirmed`.

Note: `codechecker_suppress` does the same as `codechecker_false_positive`.

You can read more about review status [here](https://github.com/Ericsson/codechecker/blob/master/www/userguide/userguide.md#userguide-review-status)

## Change review status of a specific checker result
```cpp
void test() {
  int x;
  // codechecker_confirmed [deadcode.DeadStores] suppress deadcode
  x = 1; // warn
}
```

## Change review status of all checker result
```cpp
void test() {
  int x;
  // codechecker_false_positive [all] suppress all checker results
  x = 1; // warn
}
```

## Change review status of all checker result with C style comment
```cpp
void test() {
  int x;
  /* codechecker_false_positive [all] suppress all checker results */
  x = 1; // warn
}
```

## Multi line comments
```cpp
void test() {
  int x;

  // codechecker_suppress [all] suppress all
  // checker resuls
  // with a long
  // comment
  x = 1; // warn
}
```

## Multi line C style comments
```cpp
void test() {
  int x;

  /* codechecker_suppress [all] suppress all
  checker resuls
  with a long
  comment */
  x = 1; // warn
}
```

```cpp
void test() {
  int x;

  /*
    codechecker_suppress [all] suppress all
    checker resuls
    with a long
    comment
  */
  x = 1; // warn
}
```

## Exporting source code suppression to suppress file <a name="suppress-file"></a>

```
  --export-source-suppress
                        Write suppress data from the suppression annotations
                        found in the source files that were analyzed earlier
                        that created the results.
```

```sh
CodeChecker parse ./my_plists --suppress generated.suppress --export-source-suppress
```

# Advanced usage <a name="advanced-usage"></a>

## Run CodeChecker distributed in a cluster <a name="distributed-in-cluster"></a>

You may want to configure CodeChecker to do the analysis on separate machines in a distributed way.
Start the postgres database on a central machine (in this example it is called codechecker.central) on a remotely accessible address and port and then run
```CodeChecker check``` on multiple machines (called host1 and host2), specify the remote dbaddress and dbport and use the same run name.

Create and start an empty database to which the CodeChecker server can connect.

## Setup PostgreSQL (one time only) <a name="pgsql"></a>

Before the first use, you have to setup PostgreSQL.
PostgreSQL stores its data files in a data directory, so before you start the PostgreSQL server you have to create and init this data directory.
I will call the data directory to pgsql_data.

Do the following steps:

```sh
# on machine codechecker.central

mkdir -p /path/to/pgsql_data
initdb -U codechecker -D /path/to/pgsql_data -E "SQL_ASCII"
# Start PostgreSQL server on port 5432
postgres -U codechecker -D /path/to/pgsql_data -p 5432 &>pgsql_log &
# Start the central CodeChecker server
CodeChecker server -w ~/codechecker_workspace --dbaddress localhost --dbport 5432 --view-port 8001
```

## Run CodeChecker on multiple hosts <a name="multiple-hosts"></a>

Then you can run CodeChecker on multiple hosts but using the same run name (in this example this is called "distributed_run".
CodeChecker server is listening on codechecker.central port 8001.

```sh
# On host1 we check module1
CodeChecker check -w /tmp/codechecker_ws -b "cd module_1;make" --port 8001 --host codechecker.central distributed_run

# On host2 we check module2
CodeChecker check -w /tmp/codechecker_ws -b "cd module_2;make" --port 8001 --host codechecker.central disributed_run
```

### PostgreSQL authentication (optional) <a name="pgsql-auth"></a>

If a CodeChecker is run with a user that needs database authentication, the
PGPASSFILE environment variable should be set to a pgpass file
For format and further information see PostgreSQL documentation:
http://www.postgresql.org/docs/current/static/libpq-pgpass.html

# Debugging CodeChecker <a name="debug"></a>

To change the log levels check out the [logging](logging.md) documentation.
