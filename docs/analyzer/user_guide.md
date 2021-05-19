Table of Contents
=================
* [Easy analysis wrappers](#easy-analysis-wrappers)
    * [`check`](#check)
* [Available CodeChecker analyzer subcommands](#available-analyzer-commands)
    * [`log`](#log)
        * [BitBake](#bitbake)
        * [CCache](#ccache)
        * [intercept-build](#intercept-build)
        * [Bazel](#bazel)
    * [`analyze`](#analyze)
        * [_Skip_ file](#skip)
            * [Absolute path examples](#skip-abs-example)
            * [Relative or partial path examples](#skip-rel-example)
        * [CodeChecker analyzer configuration](#analyzer-configuration)
            * [Configuration file](#analyzer-configuration-file)
            * [Analyzer and checker config options](#analyzer-checker-config-option)
              * [Configuration of analyzer tools](#analyzer-config-option)
              * [Configuration of checkers](#checker-config-option)
            * [Forwarding compiler options](#forwarding-compiler-options)
              * [_Clang Static Analyzer_](#clang-static-analyzer)
              * [_Clang-Tidy_](#clang-tidy)
            * [Compiler-specific include path and define detection (cross compilation)](#include-path)
        * [Toggling checkers](#toggling-checkers)
            * [Checker profiles](#checker-profiles)
            * [`--enable-all`](#enable-all)
        * [Toggling compiler warnings](#toggling-warnings)
        * [Cross Translation Unit (CTU) analysis mode](#ctu)
        * [Statistical analysis mode](#statistical)
    * [`parse`](#parse)
        * [Exporting source code suppression to suppress file](#suppress-file)
    * [`fixit`](#fixit)
    * [`checkers`](#checkers)
    * [`analyzers`](#analyzers)
 * [`Configuring Clang version`](#clang_version)
 * [Source code comments (review status)](#source-code-comments)
    * [Supported formats](#supported-formats)

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
`--print-steps`.

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

<details>
  <summary>
    <i>$ <b>CodeChecker check --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker check [-h] [-o OUTPUT_DIR] [-t {plist}] [-q]
                         [--keep-gcc-include-fixed] [--keep-gcc-intrin]
                         (-b COMMAND | -l LOGFILE) [-j JOBS] [-c]
                         [--compile-uniqueing COMPILE_UNIQUEING]
                         [--report-hash {context-free,context-free-v2}]
                         [-i SKIPFILE | --file FILE [FILE ...]]
                         [--analyzers ANALYZER [ANALYZER ...]]
                         [--capture-analysis-output] [--generate-reproducer]
                         [--config CONFIG_FILE]
                         [--saargs CLANGSA_ARGS_CFG_FILE]
                         [--tidyargs TIDY_ARGS_CFG_FILE]
                         [--tidy-config TIDY_CONFIG]
                         [--analyzer-config [ANALYZER_CONFIG [ANALYZER_CONFIG ...]]]
                         [--checker-config [CHECKER_CONFIG [CHECKER_CONFIG ...]]]
                         [--timeout TIMEOUT]
                         [--ctu | --ctu-collect | --ctu-analyze]
                         [--ctu-reanalyze-on-failure]
                         [--ctu-ast-mode {load-from-pch,parse-on-demand}]
                         [-e checker/group/profile] [-d checker/group/profile]
                         [--enable-all] [--print-steps] [--suppress SUPPRESS]
                         [--review-status [REVIEW_STATUS [REVIEW_STATUS ...]]]
                         [--verbose {info,debug,debug_analyzer}]

Run analysis for a project with printing results immediately on the standard
output. Check only needs a build command or an already existing logfile and
performs every step of doing the analysis in batch.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output OUTPUT_DIR
                        Store the analysis output in the given folder. If it
                        is not given then the results go into a temporary
                        directory which will be removed after the analysis.
  -t {plist}, --type {plist}, --output-format {plist}
                        Specify the format the analysis results should use.
                        (default: plist)
  -q, --quiet           If specified, the build tool's and the analyzers'
                        output will not be printed to the standard output.
  --keep-gcc-include-fixed
                        There are some implicit include paths which are only
                        used by GCC (include-fixed). This flag determines
                        whether these should be kept among the implicit
                        include paths. (default: False)
  --keep-gcc-intrin     There are some implicit include paths which contain
                        GCC-specific header files (those which end with
                        intrin.h). This flag determines whether these should
                        be kept among the implicit include paths. Use this
                        flag if Clang analysis fails with error message
                        related to __builtin symbols. (default: False)
  --compile-uniqueing COMPILE_UNIQUEING
                        Specify the method the compilation actions in the
                        compilation database are uniqued before analysis. CTU
                        analysis works properly only if there is exactly one
                        compilation action per source file. none(default in
                        non CTU mode): no uniqueing is done. strict: no
                        uniqueing is done, and an error is given if there is
                        more than one compilation action for a source file.
                        alpha(default in CTU mode): If there is more than one
                        compilation action for a source file, only the one is
                        kept that belongs to the alphabetically first
                        compilation target. If none of the above given, this
                        parameter should be a python regular expression.If
                        there is more than one compilation action for a
                        source, only the one is kept which matches the given
                        python regex. If more than one matches an error is
                        given. The whole compilation action text is searched
                        for match. (default: none)
  --review-status [REVIEW_STATUS [REVIEW_STATUS ...]]
                        Filter results by review statuses. Valid values are:
                        confirmed, false_positive, intentional, suppress,
                        unreviewed (default: ['confirmed', 'unreviewed'])
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.

log arguments:

  Specify how the build information database should be obtained. You need to
  specify either an already existing log file, or a build command which will be
  used to generate a log file on the fly.

  -b COMMAND, --build COMMAND
                        Execute and record a build command. Build commands can
                        be simple calls to 'g++' or 'clang++' or 'make', but a
                        more complex command, or the call of a custom script
                        file is also supported.
  -l LOGFILE, --logfile LOGFILE
                        Use an already existing JSON compilation command
                        database file specified at this path.

analyzer arguments:
  -j JOBS, --jobs JOBS  Number of threads to use in analysis. More threads
                        mean faster analysis at the cost of using more memory.
                        (default: <CPU count>)
  -c, --clean           Delete analysis reports stored in the output
                        directory. (By default, CodeChecker would keep reports
                        and overwrites only those files that were update by
                        the current build command).
  --report-hash {context-free,context-free-v2}
                        Specify the hash calculation method for reports. By
                        default the calculation method for Clang Static
                        Analyzer is context sensitive and for Clang Tidy it is
                        context insensitive.
                        You can use the following calculation methods:
                        - context-free: there was a bug and for Clang Tidy not
                        the context free hash was generated (kept for backward
                        compatibility).
                        - context-free-v2: context free hash is used for
                        ClangSA and Clang Tidy.
                        See the 'issue hashes' section of the help message of
                        this command below for more information.
                        USE WISELY AND AT YOUR OWN RISK!
  -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                        Path to the Skipfile dictating which project files
                        should be omitted from analysis. Please consult the
                        User guide on how a Skipfile should be laid out.
  --file FILE [FILE ...]
                        Analyze only the given file(s) not the whole
                        compilation database. Absolute directory paths should
                        start with '/', relative directory paths should start
                        with '*' and it can contain path glob pattern.
                        Example: '/path/to/main.cpp', 'lib/*.cpp', */test*'.
  --analyzers ANALYZER [ANALYZER ...]
                        Run analysis only with the analyzers specified.
                        Currently supported analyzers are: clangsa, clang-
                        tidy.
  --capture-analysis-output
                        Store standard output and standard error of successful
                        analyzer invocations into the '<OUTPUT_DIR>/success'
                        directory.
  --generate-reproducer
                        Collect all necessary information for reproducing an
                        analysis action. The gathered files will be stored in a
                        folder named 'reproducer' under the report directory.
                        When this flag is used, 'failed' directory remains
                        empty.
  --config CONFIG_FILE  Allow the configuration from an explicit JSON based
                        configuration file. The value of the 'analyzer' key in
                        the config file will be emplaced as command line
                        arguments. The format of configuration file is:
                        {
                          "analyze": [
                            "--enable=core.DivideZero",
                            "--enable=core.CallAndMessage",
                            "--report-hash=context-free-v2",
                            "--verbose=debug",
                            "--skip=$HOME/project/skip.txt",
                            "--clean"
                          ]
                        }.
                        You can use any environment variable inside this file
                        and it will be expaneded. (default: None)
  --saargs CLANGSA_ARGS_CFG_FILE
                        File containing argument which will be forwarded
                        verbatim for the Clang Static analyzer.
  --tidyargs TIDY_ARGS_CFG_FILE
                        File containing argument which will be forwarded
                        verbatim for the Clang-Tidy analyzer.
  --tidy-config TIDY_CONFIG
                        A file in YAML format containing the configuration of
                        clang-tidy checkers. The file can be dumped by
                        'CodeChecker analyzers --dump-config clang-tidy'
                        command.
  --analyzer-config [ANALYZER_CONFIG [ANALYZER_CONFIG ...]]
                        Analyzer configuration options in the following
                        format: analyzer:key=value. The collection of the
                        options can be printed with 'CodeChecker analyzers
                        --analyzer-config'. To disable the default behaviour
                        of this option you can use the 'clang-tidy:take-
                        config-from-directory=true' option. If the file at
                        --tidyargs contains a -config flag then those options
                        extend these and override "HeaderFilterRegex" if any.
                        (default: ['clang-tidy:HeaderFilterRegex=.*'])
  --checker-config [CHECKER_CONFIG [CHECKER_CONFIG ...]]
                        Checker configuration options in the following format:
                        analyzer:key=value. The collection of the options can
                        be printed with 'CodeChecker checkers --checker-
                        config'.
  --timeout TIMEOUT     The amount of time (in seconds) that each analyzer can
                        spend, individually, to analyze the project. If the
                        analysis of a particular file takes longer than this
                        time, the analyzer is killed and the analysis is
                        considered as a failed one.
  --z3 {on,off}         Enable the z3 solver backend. This allows reasoning
                        over more complex queries, but performance is worse
                        than the default range-based constraint solver.
                        (default: off)
  --z3-refutation {on,off}
                        Switch on/off the Z3 SMT Solver backend to reduce
                        false positives. The results of the ranged based
                        constraint solver in the Clang Static Analyzer will be
                        cross checked with the Z3 SMT solver. This should not
                        cause that much of a slowdown compared to using the Z3
                        solver only. (default: on)

cross translation unit analysis arguments:

  These arguments are only available if the Clang Static Analyzer supports
  Cross-TU analysis. By default, no CTU analysis is run when 'CodeChecker check'
  is called.

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
  --ctu-reanalyze-on-failure
                        If Cross-TU analysis is enabled and fails for some
                        reason, try to re analyze the same translation unit
                        without Cross-TU enabled.
  --ctu-ast-mode {load-from-pch,parse-on-demand}
                        Choose the way ASTs are loaded during CTU analysis. Only
                        available if CTU mode is enabled. Mode 'load-from-pch'
                        generates PCH format serialized ASTs during the
                        'collect' phase. Mode 'parse-on-demand' only generates
                        the invocations needed to parse the ASTs. Mode
                        'load-from-pch' can use significant disk-space for the
                        serialized ASTs, while mode 'parse-on-demand' can incur
                        some runtime CPU overhead in the second phase of the
                        analysis. (default: parse-on-demand)

checker configuration:

  Checkers
  ------------------------------------------------
  The analyzer performs checks that are categorized into families or "checkers".
  See 'CodeChecker checkers' for the list of available checkers. You can
  fine-tune which checkers to use in the analysis by setting the enabled and
  disabled flags starting from the bigger groups and going inwards, e.g.
  '-e core -d core.uninitialized -e core.uninitialized.Assign' will enable every
  'core' checker, but only 'core.uninitialized.Assign' from the
  'core.uninitialized' group. Please consult the manual for details. Disabling
  certain checkers - such as the 'core' group - is unsupported by the LLVM/Clang
  community, and thus discouraged.

  Compiler warnings and errors
  ------------------------------------------------
  Compiler warnings are diagnostic messages that report constructions that are
  not inherently erroneous but that are risky or suggest there may have been an
  error. Compiler warnings are named 'clang-diagnostic-<warning-option>', e.g.
  Clang warning controlled by '-Wliteral-conversion' will be reported with check
  name 'clang-diagnostic-literal-conversion'. You can fine-tune which warnings to
  use in the analysis by setting the enabled and disabled flags starting from the
  bigger groups and going inwards, e.g. '-e Wunused -d Wno-unused-parameter' will
  enable every 'unused' warnings except 'unused-parameter'. These flags should
  start with a capital 'W' or 'Wno-' prefix followed by the waning name (E.g.:
  '-e Wliteral-conversion', '-d Wno-literal-conversion'). By default '-Wall' and
  '-Wextra' warnings are enabled. For more information see:
  https://clang.llvm.org/docs/DiagnosticsReference.html.
  Sometimes GCC is more permissive than Clang, so it is possible that a specific
  construction doesn't compile with Clang but compiles with GCC. These
  compiler errors are also collected as CodeChecker reports as
  'clang-diagnostic-error'.
  Note that compiler errors and warnings are captured by CodeChecker only if it
  was emitted by clang-tidy.

  Profiles
  ------------------------------------------------
  In CodeCheckers there is a manual grouping of checkers. These groups are
  called profiles. The collection of profiles is found in
  config/checker_profile_map.json file. The goal of these profile is that you
  can enable or disable checkers by these profiles. See the output of
  "CodeChecker checkers --profile list" command.

  Guidelines
  ------------------------------------------------
  There are several coding guidelines like CppCoreGuideline, SEI-CERT, etc.
  These are collections of best programming practices to avoid common
  programming errors. Some checkers cover the rules of these guidelines. In
  CodeChecker there is a mapping between guidelines and checkers. This way you
  can list and enable those checkers which check the fulfillment of certain
  guideline rules. See the output of "CodeChecker checkers --guideline"
  command.

  -e checker/group/profile, --enable checker/group/profile
                        Set a checker (or checker group), profile or guideline
                        to BE USED in the analysis. In case of ambiguity the
                        priority order is profile, guideline, checker name
                        (e.g. security means the profile, not the checker
                        group). Profiles and guidelines can be labeled:
                        'profile:security' or 'guideline:sei-cert'.
  -d checker/group/profile, --disable checker/group/profile
                        Set a checker (or checker group), profile or guideline
                        to BE PROHIBITED from use in the analysis. In case of
                        ambiguity the priority order is profile, guideline,
                        checker name (e.g. security means the profile, not the
                        checker group). Profiles and guidelines can be
                        labeled: 'profile:security' or 'guideline:sei-cert'.
  --enable-all          Force the running analyzers to use almost every
                        checker available. The checker groups 'alpha.',
                        'debug.','osx.', 'abseil-', 'android-', 'darwin-',
                        'objc-', 'cppcoreguidelines-', 'fuchsia.', 'fuchsia-',
                        'hicpp-', 'llvm-', 'llvmlibc-', 'google-', 'zircon-',
                        'osx.' (on Linux) are NOT enabled automatically and
                        must be EXPLICITLY specified. WARNING! Enabling all
                        checkers might result in the analysis losing precision
                        and stability, and could even result in a total
                        failure of the analysis. USE WISELY AND AT YOUR OWN
                        RISK!

output arguments:
  --print-steps         Print the steps the analyzers took in finding the
                        reported defect.
  --suppress SUPPRESS   Path of the suppress file to use. Records in the
                        suppress file are used to suppress the display of
                        certain results when parsing the analyses' report.
                        (Reports to an analysis result can also be suppressed
                        in the source code -- please consult the manual on how
                        to do so.) NOTE: The suppress file relies on the "bug
                        identifier" generated by the analyzers which is
                        experimental, take care when relying on it.

Environment variables
------------------------------------------------
Environment variables for 'CodeChecker log' command:

  CC_LOGGER_ABS_PATH       If the environment variable is defined, all relative
                           paths in the compilation commands after '-I,
                           -idirafter, -imultilib, -iquote, -isysroot -isystem,
                           -iwithprefix, -iwithprefixbefore, -sysroot,
                           --sysroot' will be converted to absolute PATH when
                           written into the compilation database.
  CC_LOGGER_DEBUG_FILE     Output file to print log messages. By default if we
                           run the log command in debug mode it will generate
                           a 'codechecker.logger.debug' file beside the log
                           file.
  CC_LOGGER_DEF_DIRS       If the environment variable is defined, the logger
                           will extend the compiler argument list in the
                           compilation database with the pre-configured include
                           paths of the logged compiler.
  CC_LOGGER_GCC_LIKE       Set to to a colon separated list to change which
                           compilers should be logged. For example (default):
                           export CC_LOGGER_GCC_LIKE="gcc:g++:clang:clang++:
                           cc:c++". The logger will match any compilers with
                           'gcc', 'g++', 'clang', 'clang++', 'cc' and 'c++' in
                           their filenames.
  CC_LOGGER_KEEP_LINK      If its value is not 'true' then object files will be
                           removed from the build action. For example in case
                           of this build command: 'gcc main.c object1.o
                           object2.so' the 'object1.o' and 'object2.so' will be
                           removed and only 'gcc main.c' will be captured. If
                           only object files are provided to the compiler then
                           the complete build action will be thrown away. This
                           means that build actions which only perform linking
                           will not be captured. We consider a file as object
                           file if its extension is '.o', '.so' or '.a'.

Environment variables for 'CodeChecker analyze' command:

  CC_ANALYZERS_FROM_PATH   Set to `yes` or `1` to enforce taking the analyzers
                           from the `PATH` instead of the given binaries.
  CC_CLANGSA_PLUGIN_DIR    If the CC_ANALYZERS_FROM_PATH environment variable
                           is set you can configure the plugin directory of the
                           Clang Static Analyzer by using this environment
                           variable.
  CC_SEVERITY_MAP_FILE     Path of the checker-severity mapping config file.
                           Default: <package>/config/checker_severity_map.json

Environment variables for 'CodeChecker parse' command:

  CC_CHANGED_FILES       Path of changed files json from Gerrit. Use it when
                         generating gerrit output.
  CC_REPO_DIR            Root directory of the sources, i.e. the directory
                         where the repository was cloned. Use it when
                         generating gerrit output.
  CC_REPORT_URL          URL where the report can be found. Use it when
                         generating gerrit output.
  CC_SEVERITY_MAP_FILE   Path of the checker-severity mapping config file.
                         Default: <package>/config/checker_severity_map.json

Issue hashes
------------------------------------------------
- By default the issue hash calculation method for 'Clang Static Analyzer' is
context sensitive. It means the hash will be generated based on the following
information:
  * signature of the enclosing function declaration, type declaration or
    namespace.
  * content of the line where the bug is.
  * unique name of the checker.
  * position (column) within the line.

- By default the issue hash calculation method for 'Clang Tidy' is context
insensitive. It means the hash will be generated based on the following
information:
  * 'file name' from the main diag section.
  * 'checker name'.
  * 'checker message'.
  * 'line content' from the source file if can be read up.
  * 'column numbers' from the main diag section.
  * 'range column numbers' only from the control diag sections if column number
    in the range is not the same as the previous control diag section number in
    the bug path. If there are no control sections event section column numbers
    are used.

- context-free: there was a bug and for Clang Tidy the default hash was
generated and not the context free hash (kept for backward compatibility). Use
'context-free-v2' instead of this.

- context-free-v2:
  * 'file name' from the main diag section.
  * 'checker message'.
  * 'line content' from the source file if can be read up. All the whitespaces
    from the source content are removed.
  * 'column numbers' from the main diag sections location.

OUR RECOMMENDATION: we recommend you to use 'context-free-v2' hash because the
hash will not be changed so easily for example on code indentation or when a
checker is renamed.

For more information see:
https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/report_identification.md

Exit status
------------------------------------------------
0 - No report
1 - CodeChecker error
2 - At least one report emitted by an analyzer
3 - Analysis of at least one translation unit failed
128+signum - Terminating on a fatal signal whose number is signum

If you wish to reuse the logfile resulting from executing the build, see
'CodeChecker log'. To keep analysis results for later, see and use
'CodeChecker analyze'. To print human-readable output from previously saved
analysis results, see 'CodeChecker parse'. 'CodeChecker check' exposes a
wrapper calling these three commands in succession. Please make sure your build
command actually builds the files -- it is advised to execute builds on empty
trees, aka. after a 'make clean', as CodeChecker only analyzes files that had
been used by the build system.
```
</details>

# Available CodeChecker analyzer subcommands <a name="available-analyzer-commands"></a>

## `log` <a name="log"></a>

The first step in performing an analysis on your project is to record
information about the files in your project for the analyzers. This is done by
recording a build of your project, which is done by the command `CodeChecker
log`.

<details>
  <summary>
    <i>$ <b>CodeChecker log --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker log [-h] -o LOGFILE -b COMMAND [-q]
                       [--verbose {info,debug,debug_analyzer}]

Runs the given build command and records the executed compilation steps. These
steps are written to the output file in a JSON format. Available build logger
tool that will be used is '...'. ld-logger can be fine-tuned with some
environment variables. For details see the following documentation:
https://github.com/Ericsson/codechecker/blob/master/analyzer/tools/build-
logger/README.md#usage

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

Environment variables
------------------------------------------------

  CC_LOGGER_ABS_PATH       If the environment variable is defined, all relative
                           paths in the compilation commands after '-I,
                           -idirafter, -imultilib, -iquote, -isysroot -isystem,
                           -iwithprefix, -iwithprefixbefore, -sysroot,
                           --sysroot' will be converted to absolute PATH when
                           written into the compilation database.
  CC_LOGGER_DEBUG_FILE     Output file to print log messages. By default if we
                           run the log command in debug mode it will generate
                           a 'codechecker.logger.debug' file beside the log
                           file.
  CC_LOGGER_DEF_DIRS       If the environment variable is defined, the logger
                           will extend the compiler argument list in the
                           compilation database with the pre-configured include
                           paths of the logged compiler.
  CC_LOGGER_GCC_LIKE       Set to to a colon separated list to change which
                           compilers should be logged. For example (default):
                           export CC_LOGGER_GCC_LIKE="gcc:g++:clang:clang++:
                           cc:c++". The logger will match any compilers with
                           'gcc', 'g++', 'clang', 'clang++', 'cc' and 'c++' in
                           their filenames.
  CC_LOGGER_KEEP_LINK      If its value is not 'true' then object files will be
                           removed from the build action. For example in case
                           of this build command: 'gcc main.c object1.o
                           object2.so' the 'object1.o' and 'object2.so' will be
                           removed and only 'gcc main.c' will be captured. If
                           only object files are provided to the compiler then
                           the complete build action will be thrown away. This
                           means that build actions which only perform linking
                           will not be captured. We consider a file as object
                           file if its extension is '.o', '.so' or '.a'.
```
</details>

Please note, that only the files that are used in the given `--build` argument
will be recorded. To analyze your whole project, make sure your build tree has
been cleaned before executing `log`.

You can change the compilers that should be logged.
Set `CC_LOGGER_GCC_LIKE` environment variable to a colon separated list.
For example (default):

```sh
export CC_LOGGER_GCC_LIKE="gcc:g++:clang:clang++:cc:c++"
```

This colon separated list may contain compiler names or paths. In case an
element of this list contains at least one slash (/) character then this is
considered a path. The logger will capture only those build actions which have
this postfix:

```sh
export CC_LOGGER_GCC_LIKE="gcc:/bin/g++:clang:clang++:cc:c++"

# "gcc" has to be infix of the compiler's name because it contains no slash.
# "/bin/g++" has to be postfix of the compiler's path because it contains slash.

my/gcc/compiler/g++ main.cpp  # Not captured because there is no match.
my/gcc/compiler/gcc-7 main.c  # Captured because "gcc" is infix of "gcc-7".
/usr/bin/g++ main.cpp         # Captured because "/bin/g++" is postfix of the compiler path.
/usr/bin/g++-7 main.cpp       # Not captured because "/bin/g++" is not postfix of the compiler path.

# For an exact compiler binary name match start the binary name with a "/".
/clang # Will not log clang++ calls only the clang binary calls will be captured.
clang  # Will capture clang-tidy (which is not wanted) calls too because of a partial match.
```

Example:

```sh
CodeChecker log -o ../codechecker_myProject_build.log -b "make -j2"
```

If you run CodeChecker log in verbose mode (`debug` or `debug_analyzer`) it
will create a 'codechecker.logger.debug' debug log file beside the given output
file. It will contain debug information of compilation database generation. You
can override this file if you set the `CC_LOGGER_DEBUG_FILE` environment
variable to a different file path.

```sh
export CC_LOGGER_DEBUG_FILE="/path/to/codechecker.debug.log"
```

With `CC_LOGGER_KEEP_LINK` environment variable you can set whether linking
build actions (i.e. those which don't perform compilation but contain only
object files as input) should be captured. For further details see
[this documentation](/analyzer/tools/build-logger/README.md).


### Change user inside the build command
If we change user inside the build command of the CodeChecker log command
before the actual compiler invocation, the compilation database will be empty:

```sh
CodeChecker log -o compile_commands.json -b "su myuser  -c 'g++ main.cpp -o /dev/null'"
```

The problem here is that the compilation database file and the lock file will
be created with the user who runs the CodeChecker log command and only this
user will have permission to read/write these files. A solution can be if we
change a user before the CodeChecker log command:

```sh
# Create a directory for compilation database.
mkdir -p log_dir

# Change file owner of log_dir.
chown myuser log_dir

# Run the command.
su myuser  -c "CodeChecker log -o log_dir/compile_commands.json -b 'g++ main.cpp -o /dev/null'"
```


### BitBake

Note: for an alternative integration, check-out [meta-codechecker](https://github.com/dl9pf/meta-codechecker).

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

### intercept-build <a name="intercept-build"></a>
[`intercept-build`](https://github.com/rizsotto/scan-build) is an alternative
tool for logging the compilation actions. Note that its first version (1.1) had
a bug in case the original build command contained a space character:
```bash
intercept-build bash -c 'g++ -DVARIABLE="hello world" main.cpp'
```
When analysing this build action, CodeChecker will most probably give a
compilation error on the underlying Clang invocation.


### Bazel <a name="bazel"></a>
Do the following steps to log compiler calls made by
[Bazel](https://www.bazel.build/) using CodeChecker.

1) We need to deactivate the
["sandbox"](https://bazel.build/designs/2016/06/02/sandboxing.html)
mechanism of *Bazel*:

- Use [`--batch`](https://docs.bazel.build/versions/2.0.0/user-manual.html#flag--batch)
mode. Batch mode causes Bazel to not use the standard client/server mode
instead running a bazel java process for a single command.
- Use [`--spawn_strategy=local`](https://docs.bazel.build/versions/2.0.0/user-manual.html#flag--spawn_strategy)
option which causes commands to be executed as local subprocesses.
- Use [`--strategy=Genrule=strategy`](https://docs.bazel.build/versions/2.0.0/user-manual.html#flag--genrule_strategy)
option.

2) Keep the following environment variables:

- `LD_LIBRARY_PATH`
- `LD_PRELOAD`
- `CC_LOGGER_GCC_LIKE`
- `CC_LOGGER_FILE`


```bash
CodeChecker log -o ./compile_commands.json -b \
  "bazel --batch \
   build \
     --spawn_strategy=local \
     --strategy=Genrule=local \
     --action_env=LD_PRELOAD=\$LD_PRELOAD \
     --action_env=LD_LIBRARY_PATH=\$LD_LIBRARY_PATH \
     --action_env=CC_LOGGER_GCC_LIKE=\$CC_LOGGER_GCC_LIKE \
     --action_env=CC_LOGGER_FILE=\$CC_LOGGER_FILE \
   //main:hello-world"
```

**Note**: If you would like to create a compilation database for your full build do not
forget to [clear](https://docs.bazel.build/versions/master/user-manual.html#clean)
your project first: `bazel clean --expunge`.


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

<details>
  <summary>
    <i>$ <b>CodeChecker analyze --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker analyze [-h] [-j JOBS]
                           [-i SKIPFILE | --file FILE [FILE ...]] -o
                           OUTPUT_PATH
                           [--compiler-info-file COMPILER_INFO_FILE]
                           [--keep-gcc-include-fixed] [--keep-gcc-intrin]
                           [-t {plist}] [-q] [-c]
                           [--compile-uniqueing COMPILE_UNIQUEING]
                           [--report-hash {context-free,context-free-v2}]
                           [-n NAME] [--analyzers ANALYZER [ANALYZER ...]]
                           [--add-compiler-defaults]
                           [--capture-analysis-output] [--generate-reproducer]
                           [--config CONFIG_FILE]
                           [--saargs CLANGSA_ARGS_CFG_FILE]
                           [--tidyargs TIDY_ARGS_CFG_FILE]
                           [--tidy-config TIDY_CONFIG] [--timeout TIMEOUT]
                           [--ctu | --ctu-collect | --ctu-analyze]
                           [--ctu-ast-mode {load-from-pch, parse-on-demand}]
                           [--ctu-reanalyze-on-failure]
                           [-e checker/group/profile]
                           [-d checker/group/profile] [--enable-all]
                           [--verbose {info,debug,debug_analyzer}]
                           logfile

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
                        (default: <CPU count>)
  -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                        Path to the Skipfile dictating which project files
                        should be omitted from analysis. Please consult the
                        User guide on how a Skipfile should be laid out.
  --file FILE [FILE ...]
                        Analyze only the given file(s) not the whole
                        compilation database. Absolute directory paths should
                        start with '/', relative directory paths should start
                        with '*' and it can contain path glob pattern.
                        Example: '/path/to/main.cpp', 'lib/*.cpp', */test*'.
  -o OUTPUT_PATH, --output OUTPUT_PATH
                        Store the analysis output in the given folder.
  --compiler-info-file COMPILER_INFO_FILE
                        Read the compiler includes and target from the
                        specified file rather than invoke the compiler
                        executable.
  --keep-gcc-include-fixed
                        There are some implicit include paths which
                        are only used by GCC (include-fixed). This flag
                        determines whether these should be kept among the
                        implicit include paths. (default: False)
  --keep-gcc-intrin     There are some implicit include paths which contain
                        GCC-specific header files (those which end with
                        intrin.h). This flag determines whether these should
                        be kept among the implicit include paths. Use this
                        flag if Clang analysis fails with error message
                        related to __builtin symbols. (default: False)
  -t {plist}, --type {plist}, --output-format {plist}
                        Specify the format the analysis results should use.
                        (default: plist)
  --makefile            Generate a Makefile in the given output directory from
                        the analyzer commands and do not execute the analysis.
                        The analysis can be executed by calling the make
                        command like 'make -f output_dir/Makefile'. You can
                        ignore errors with the -i/--ignore-errors options:
                        'make -f output_dir/Makefile -i'. (default: False)
  -q, --quiet           Do not print the output or error of the analyzers to
                        the standard output of CodeChecker.
  -c, --clean           Delete analysis reports stored in the output
                        directory. (By default, CodeChecker would keep reports
                        and overwrites only those files that were update by
                        the current build command).
  --compile-uniqueing COMPILE_UNIQUEING
                        Specify the method the compilation actions in the
                        compilation database are uniqued before analysis. CTU
                        analysis works properly only if there is exactly one
                        compilation action per source file. none(default in
                        non CTU mode): no uniqueing is done. strict: no
                        uniqueing is done, and an error is given if there is
                        more than one compilation action for a source file.
                        alpha(default in CTU mode): If there is more than one
                        compilation action for a source file, only the one is
                        kept that belongs to the alphabetically first
                        compilation target. If none of the above given, this
                        parameter should be a python regular expression.If
                        there is more than one compilation action for a
                        source, only the one is kept which matches the given
                        python regex. If more than one matches an error is
                        given. The whole compilation action text is searched
                        for match. (default: none)
--report-hash {context-free,context-free-v2}
                        Specify the hash calculation method for reports. By
                        default the calculation method for Clang Static
                        Analyzer is context sensitive and for Clang Tidy it is
                        context insensitive.
                        You can use the following calculation methods:
                        - context-free: there was a bug and for Clang Tidy not
                        the context free hash was generated (kept for backward
                        compatibility).
                        - context-free-v2: context free hash is used for
                        ClangSA and Clang Tidy.
                        See the 'issue hashes' section of the help message of
                        this command below for more information.
                        USE WISELY AND AT YOUR OWN RISK!
  -n NAME, --name NAME  Annotate the run analysis with a custom name in the
                        created metadata file.
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.

Environment variables
------------------------------------------------

  CC_ANALYZERS_FROM_PATH   Set to `yes` or `1` to enforce taking the analyzers
                           from the `PATH` instead of the given binaries.
  CC_CLANGSA_PLUGIN_DIR    If the CC_ANALYZERS_FROM_PATH environment variable
                           is set you can configure the plugin directory of the
                           Clang Static Analyzer by using this environment
                           variable.
  CC_SEVERITY_MAP_FILE     Path of the checker-severity mapping config file.
                           Default: <package>/config/checker_severity_map.json
```
</details>


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

Please note that when `-i SKIPFILE` is used along with `--stats` or
`--ctu` the skip list will be ignored in the pre-analysis phase. This means
that statistics and ctu-pre-analysis will be created for *all* files in the
*compilation database*.

### CodeChecker analyzer configuration <a name="analyzer-configuration"></a>

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
  --generate-reproducer
                        Collect all necessary information for reproducing an
                        analysis action. The gathered files will be stored in a
                        folder named 'reproducer' under the report directory.
                        When this flag is used, 'failed' directory remains
                        empty.
  --config CONFIG_FILE  Allow the configuration from an explicit JSON based
                        configuration file. The value of the 'analyzer' key in
                        the config file will be emplaced as command line
                        arguments. The format of configuration file is:
                        {
                          "analyze": [
                            "--enable=core.DivideZero",
                            "--enable=core.CallAndMessage",
                            "--report-hash=context-free-v2",
                            "--verbose=debug",
                            "--skip=$HOME/project/skip.txt",
                            "--clean"
                          ]
                        }.
                        You can use any environment variable inside this file
                        and it will be expaneded. (default: None)
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
  --analyzer-config [ANALYZER_CONFIG [ANALYZER_CONFIG ...]]
                        Analyzer configuration options in the following
                        format: analyzer:key=value. The collection of the
                        options can be printed with 'CodeChecker analyzers
                        --analyzer-config'. To disable the default behaviour
                        of this option you can use the 'clang-tidy:take-
                        config-from-directory=true' option. If the file at
                        --tidyargs contains a -config flag then those options
                        extend these and override "HeaderFilterRegex" if any.
                        (default: ['clang-tidy:HeaderFilterRegex=.*'])
  --checker-config [CHECKER_CONFIG [CHECKER_CONFIG ...]]
                        Checker configuration options in the following format:
                        analyzer:key=value. The collection of the options can
                        be printed with 'CodeChecker checkers
                        --checker-config'.
  --timeout TIMEOUT     The amount of time (in seconds) that each analyzer can
                        spend, individually, to analyze the project. If the
                        analysis of a particular file takes longer than this
                        time, the analyzer is killed and the analysis is
                        considered as a failed one.
  --z3 {on,off}         Enable the z3 solver backend. This allows reasoning
                        over more complex queries, but performance is worse
                        than the default range-based constraint solver.
                        (default: off)
  --z3-refutation {on,off}
                        Switch on/off the Z3 SMT Solver backend to reduce
                        false positives. The results of the ranged based
                        constraint solver in the Clang Static Analyzer will be
                        cross checked with the Z3 SMT solver. This should not
                        cause that much of a slowdown compared to using the Z3
                        solver only. (default: on)
```

CodeChecker supports several analyzer tools. Currently, these analyzers are
the [_Clang Static Analyzer_](http://clang-analyzer.llvm.org) and
[_Clang-Tidy_](http://clang.llvm.org/extra/clang-tidy). `--analyzers` can be
used to specify which analyzer tool should be used (by default, all supported
are used). The tools are completely independent, so either can be omitted if
not present as they are provided by different binaries.

See [Configure Clang Static Analyzer and checkers](checker_and_analyzer_configuration.md)
documentation for a more detailed description how to use the `saargs`,
`tidyargs` and `z3` arguments.

#### Configuration file <a name="analyzer-configuration-file"></a>
`--config` option allow the configuration from an explicit configuration file.
The parameters in the config file will be emplaced as command line arguments.

**Example**:
Lets assume you have a configuration file
[`codechecker.json`](../../config/codechecker.json) with the following content:
```json
{
  "analyze": [
    "--enable=core.DivideZero",
    "--enable=core.CallAndMessage",
    "--analyzer-config",
    "clangsa:unroll-loops=true",
    "--checker-config",
    "clang-tidy:google-readability-function-size.StatementThreshold=100"
    "--report-hash", "context-free-v2"
    "--verbose=debug",
    "--clean"
  ],
  "parse": [
    "--trim-path-prefix",
    "/$HOME/workspace"
  ],
  "server": [
    "--workspace=$HOME/workspace",
    "--port=9090"
  ],
  "store": [
    "--name=run_name",
    "--tag=my_tag",
    "--url=http://codechecker.my:9090/MyProduct"
  ]
}
```
This configuration file example contains configuration options for multiple
codechecker subcommands (analyze, parse, server, store) so not just the
`analyze` subcommand can be configured like this.
The focus is on the `analyze` subcommand configuration in the next examples.

If you run the following command:
```sh
CodeChecker analyze compilation.json -o ./reports --config ./codechecker.json
```
then the analyzer parameters from the `codechecker.json` file will be emplaced
as command line arguments:
```sh
CodeChecker analyze compilation.json -o ./reports --enable=core.DivideZero --enable=core.CallAndMessage --analyzer-config clangsa:unroll-loops=true --checker-config clang-tidy:google-readability-function-size.StatementThreshold=100 --report-hash context-free-v2 --verbose debug --clean
```

Note: Options which require parameters have to be in either of the following
formats:

- Use equal to separate option and parameter in quotes:
  `{ "analyze": [ "--verbose=debug" ] }`
- Use separated values for option and parameter:
  `{ "analyze": [ "--verbose", "debug" ] }`

Note: environment variables inside this config file will be expanded:
`{ "analyze": [ "--skip=$HOME/project/skip.txt" ] }`

#### Analyzer and checker config options <a name="analyzer-checker-config-option"></a>

CodeChecker's analyzer module currently handles ClangSA and ClangTidy. The main
purpose of this analyzer module is to hide the differences between the
interfaces and parameterization of these two tools. Both ClangSA and ClangTidy
have a set of checkers with fine-tuning config options and the analyzer tools
themselves can also be configured.

##### Configuration of analyzer tools <a name="analyzer-config-option"></a>

ClangSA performs symbolic execution which is a resource consuming method of
simulating the program run. Some heuristics are guiding the analyzer engine in
order to prevent too much memory consumption. For example the loops are not
simulated to the infinity, but at most four iterations are done. If you have
more resource, you can turn on full loop unrolling if the number of interations
is determinable by the analyzer.

To list the available analyzer config options use the following commands:
```
CodeChecker analyzers --analyzer-config <analyzer_name> --details
```
The `<analyzer_name>` can be either `clangsa` or `clang-tidy`. The available
analyzers can be listed by:
```
CodeChecker analyzers --details
```
The `--details` flag is always optional. It provides more information about
the specific output. In case of config options it gives a short description
about the option and its default value.

The output of the loop-related analyzer options is this:
```
clangsa:cfg-loopexit (bool) Whether or not the end of the loop information should be included in the CFG. (default: false)
clangsa:unroll-loops (bool) Whether the analysis should try to unroll loops with known bounds. (default: false)
clangsa:widen-loops (bool) Whether the analysis should try to widen loops. (default: false)
```

The format of passing the config option to the analyzer is:
`analyzer_name:key=value`. So if you need the loop unrolling functionality
then use the following analyzer command:

```
CodeChecker analyze build.json \
  --analyzer-config clangsa:unroll-loops=true \
  -o reports
```

##### Configuration of checkers <a href="checker-config-option"></a>

Each analyzer tool provides a set of checkers. These can be listed with the
following command:
```
CodeChecker checkers --details
```

Some of these checkers have some fine-tuning config options. For example
suppose that you'd like to rule the complexity of functions. First you can list
the available checkers and find the one which checks functions' size:
```
CodeChecker checkers --details
```
Every supported checker is reported by the `checkers` command and all of its
subcommands.

After finding `google-readability-function-size` checker, you can list the
config options with the following command:
```
CodeChecker checkers --checker-config --details
```
`--details` flag is optional again. It displays the default values and the
description of the checker options. In the list you can find the appropriate
configuration on function size. It has to be given in the same format as the
analyzer options: `analyzer_name:key=value`, but this time use the flag
`--checker-config`:
```
CodeChecker analyze build.json \
  --checker-config clang-tidy:google-readability-function-size.StatementThreshold=100 \
  -o reports
```

:exclamation: Warning: ClangTidy can be configured with a config file named
`.clang-tidy` located somewhere in the project tree. If either
`--analyzer-config` or `--checker-config` flag is given to the analyzer
command, this file will not be used at all. This is important because the
default value of `--analyzer-config` is `clang-tidy:HeaderFilterRegex=.*` which
makes ClangTidy report on issues in header files too. If you'd like to
overwrite this default value so `.clang-tidy` is used then
`--analyzer-config clang-tidy:take-config-from-directory=true` must be given.

The analyzer and checker configuration options can also be inserted in the
CodeChecker configuration file. See an example
[above](#analyzer-configuration-file).

#### Forwarding compiler options <a name="forwarding-compiler-options"></a>

In those rare cases when the specific analyzer tools need an option other than
the ones listed in the previous section, you can create a file of which the
content will be forwarded verbatim to the analyzer. The main difficulty here is
that you need to know the parameterization of the analyzers precisely. The
usage of this option is not recommended. `--analyzer-config` and
`--checker-config` is preferred over these!

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

#### Compiler-specific include path and define detection (cross compilation) <a name="include-path"></a>

Some of the include paths are hardcoded during compiler build. If a (cross)
compiler is used to build a project it is possible that the wrong include
paths are searched and the wrong headers will be included which causes
analyses to fail. These hardcoded include paths and defines can be marked for
automatically detection by specifying the `--add-compiler-defaults` flag.

CodeChecker will get the hardcoded values for the compilers set in the
`CC_LOGGER_GCC_LIKE` environment variable.

```sh
export CC_LOGGER_GCC_LIKE="gcc:g++:clang:clang++:cc:c++"
```

If there are still compilation errors after using the `--add-compiler-defaults`
argument, it is possible that the wrong build target architecture
(32bit, 64bit) is used. Please try to forward these compilation flags
to the analyzers:

 - `-m32` (32-bit build)
 - `-m64` (64-bit build)

GCC specific hard-coded values are detected during the analysis and
recorded int the `<report-directory>/compiler_info.json`.

If you want to run the analysis with a specific compiler configuration
instead of the auto-detection you can pass that to the
`--compiler-info-file compiler_info.json` parameter.

There are some standard locations which compilers use in order to find standard
header files. These paths are hard-coded in GCC compiler. CodeChecker is able
to collect these so the analysis process can run in the same environment as the
original build. However, there are some GCC-specific locations (usually with
name `include-fixed`) which may be incompatible with other compilers and may
cause failure in analysis. CodeChecker omits these GCC-specific paths from the
analysis unless `--keep-gcc-include-fixed` or `--keep-gcc-intrin` flag is
given. For further information see
[GCC incompatibilities](gcc_incompatibilities.md).

### Toggling checkers <a name="toggling-checkers"></a>

The list of checkers to be used in the analysis can be fine-tuned with the
`--enable` and `--disable` options. See `codechecker-checkers` for the list of
available checkers in the binaries installed on your system.

```
checker configuration:

  -e checker/group/profile, --enable checker/group/profile
                        Set a checker (or checker group or checker profile)
                        to BE USED in the analysis. In case of ambiguity the
                        priority order is profile, guideline, checker name
                        (e.g. security means the profile, not the checker
                        group). Profiles and guidelines can be labeled:
                        'profile:security' or 'guideline:sei-cert'.
  -d checker/group/profile, --disable checker/group/profile
                        Set a checker (or checker group or checker profile)
                        to BE PROHIBITED from use in the analysis. In case of
                        ambiguity the priority order is profile, guideline,
                        checker name (e.g. security means the profile, not the
                        checker group). Profiles and guidelines can be
                        labeled: 'profile:security' or 'guideline:sei-cert'.
  --enable-all          Force the running analyzers to use almost every
                        checker available. The checker groups 'alpha.',
                        'debug.','osx.', 'abseil-', 'android-', 'darwin-',
                        'objc-', 'cppcoreguidelines-', 'fuchsia.', 'fuchsia-',
                        'hicpp-', 'llvm-', 'llvmlibc-', 'google-', 'zircon-',
                        'osx.' (on Linux) are NOT enabled automatically and
                        must be EXPLICITLY specified. WARNING! Enabling all
                        checkers might result in the analysis losing precision
                        and stability, and could even result in a total
                        failure of the analysis. USE WISELY AND AT YOUR OWN
                        RISK!
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

Checkers are taken into account based on the following order:

- First the default state is taken based on the analyzer tool.
- Members of "default" profile are enabled.
- In case of `--enable-all` every checker is enabled except for `alpha` and
  "debug" checker groups. `osx` checker group is also not included unless the
  target platform is Darwin.
- Command line `--enable/--disable` flags.
  - Their arguments may start with `profile:` of `guideline:` prefix which
    makes the choice explicit.
  - Without prefix it means a profile name, a guideline name or a checker
    group/name in this priority order.

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

A warning can be referred in both formats: `-d Wunused-parameter` and
`-d clang-diagnostic-unused-parameter` are the same.

`clang-diagnostic-error` is a special one, since it doesn't refer a warning but
a compilation error. This is enabled by default and will be stored as a
critical severity bug.

**Note**: by default `-Wall` and `-Wextra` warnings are enabled.


#### Checker profiles <a name="checker-profiles"></a>

Checker profiles describe custom sets of enabled checks which can be specified
in the `{INSTALL_DIR}/config/checker_profile_map.json` file. Three built-in
options are available grouping checkers by their quality (measured by their
false positive rate): `default`, `sensitive` and `extreme`. In addition,
profile `portability` contains checkers for detecting platform-dependent code
issues. These issues can arise when migrating code from 32-bit to 64-bit
architectures, and the root causes of the bugs tend to be overflows, sign
extensions and widening conversions or casts. Detailed information about
profiles can be retrieved by the `CodeChecker checkers` command.

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
  --ctu-ast-mode {load-from-pch,parse-on-demand}
                        Choose the way ASTs are loaded during CTU analysis. Only
                        available if CTU mode is enabled. Mode 'load-from-pch'
                        generates PCH format serialized ASTs during the
                        'collect' phase. Mode 'parse-on-demand' only generates
                        the invocations needed to parse the ASTs. Mode
                        'load-from-pch' can use significant disk-space for the
                        serialized ASTs, while mode 'parse-on-demand' can incur
                        some runtime CPU overhead in the second phase of the
                        analysis. (default: parse-on-demand)
```

### Statistical analysis mode <a name="statistical"></a>

If the `clang` static analyzer binary in your installation supports
statistical checkers CodeChecker can execute the analyzers
with this mode enabled.

These options are only visible in `analyze` if the experimental
statistical analysis support is present.

```
Statistics analysis feature arguments:
  These arguments are only available if the Clang Static Analyzer supports
  Statistics-based analysis (e.g. statisticsCollector.ReturnValueCheck,
  statisticsCollector.SpecialReturnValue checkers are available).

  --stats-collect STATS_OUTPUT, --stats-collect STATS_OUTPUT
                        Perform the first, 'collect' phase of Statistical
                        analysis. This phase generates extra files needed by
                        statistics analysis, and puts them into
                        '<STATS_OUTPUT>'. NOTE: If this argument is present,
                        CodeChecker will NOT execute the analyzers!
  --stats-use STATS_DIR, --stats-use STATS_DIR
                        Use the previously generated statistics results for
                        the analysis from the given '<STATS_DIR>'.
  --stats               Perform both phases of Statistical analysis. This
                        phase generates extra files needed by statistics
                        analysis and enables the statistical checkers. No
                        need to enable them explicitly.
 --stats-min-sample-count STATS_MIN_SAMPLE_COUNT, --stats-min-sample-count STATS_MIN_SAMPLE_COUNT
                        Minimum number of samples (function call occurrences)
                        to be collected for a statistics to be relevant.
                        (default: 10)
  --stats-relevance-threshold STATS_RELEVANCE_THRESHOLD, --stats-relevance-threshold STATS_RELEVANCE_THRESHOLD
                        The minimum ratio of calls of function f that must
                        have a certain property to consider it true for that
                        function (calculated as calls  with a property/all
                        calls). CodeChecker will warn for calls of f that do
                        not have that property.(default: 0.85)

```

## `parse` <a name="parse"></a>

`parse` is used to read previously created machine-readable analysis results
(such as `plist` files), usually previously generated by `CodeChecker analyze`.
`parse` prints analysis results to the standard output.

<details>
  <summary>
    <i>$ <b>CodeChecker parse --help</b> (click to expand)</i>
  </summary>

```
Usage: CodeChecker parse [-h] [--config CONFIG_FILE] [-t {plist}]
                         [-e {html,json,codeclimate,gerrit}] [-o OUTPUT_PATH]
                         [--suppress SUPPRESS] [--export-source-suppress]
                         [--print-steps] [-i SKIPFILE]
                         [--trim-path-prefix [TRIM_PATH_PREFIX [TRIM_PATH_PREFIX ...]]]
                         [--review-status [REVIEW_STATUS [REVIEW_STATUS ...]]]
                         [--verbose {info,debug_analyzer,debug}]
                         file/folder [file/folder ...]

Parse and pretty-print the summary and results from one or more
'codechecker-analyze' result files. Bugs which are commented by using
"false_positive", "suppress" and "intentional" source code comments will not be
printed by the `parse` command.

positional arguments:
  file/folder           The analysis result files and/or folders containing
                        analysis results which should be parsed and printed.

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG_FILE  Allow the configuration from an explicit JSON based
                        configuration file. The value of the 'parse' key in
                        the config file will be emplaced as command line
                        arguments. The format of configuration file is:
                        {
                          "parse": [
                            "--trim-path-prefix",
                            "$HOME/workspace"
                          ]
                        } (default: None)
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
  --trim-path-prefix [TRIM_PATH_PREFIX [TRIM_PATH_PREFIX ...]]
                        Removes leading path from files which will be printed.
                        So if you have /a/b/c/x.cpp and /a/b/c/y.cpp then by
                        removing "/a/b/" prefix will print files like c/x.cpp
                        and c/y.cpp. If multiple prefix is given, the longest
                        match will be removed.
  --review-status [REVIEW_STATUS [REVIEW_STATUS ...]]
                        Filter results by review statuses. Valid values are:
                        confirmed, false_positive, intentional, suppress,
                        unreviewed (default: ['confirmed', 'unreviewed'])
  --verbose {info,debug_analyzer,debug}
                        Set verbosity level.

export arguments:
  -e {html,json,codeclimate,gerrit}, --export {html,json,codeclimate,gerrit}
                        Specify extra output format type.
                        'codeclimate' format can be used for Code Climate and
                        for GitLab integration. For more information see:
                        https://github.com/codeclimate/platform/blob/master/sp
                        ec/analyzers/SPEC.md#data-types (default: None)
  -o OUTPUT_PATH, --output OUTPUT_PATH
                        Store the output in the given folder.

Environment variables
------------------------------------------------

  CC_CHANGED_FILES       Path of changed files json from Gerrit. Use it when
                         generating gerrit output.
  CC_REPO_DIR            Root directory of the sources, i.e. the directory
                         where the repository was cloned. Use it when
                         generating gerrit output.
  CC_REPORT_URL          URL where the report can be found. Use it when
                         generating gerrit output.
  CC_SEVERITY_MAP_FILE   Path of the checker-severity mapping config file.
                         Default: <package>/config/checker_severity_map.json

Exit status
------------------------------------------------
0 - No report
1 - CodeChecker error
2 - At least one report emitted by an analyzer
```
</details>

For example, if the analysis was run like:

```sh
CodeChecker analyze ../codechecker_myProject_build.log -o my_plists
```

then the results of the analysis can be printed with

```sh
CodeChecker parse ./my_plists
```

## `fixit` <a name="fixit"></a>

ClangTidy is able to provide suggestions on automatic fixes of reported issues.
For example there is a ClangTidy checker which suggests using
`collection.empty()` instead of `collection.size() != 0` expression. These
simple changes can be applied directy in the source code. `CodeChecker fixit`
command handles these automatic fixes.

<details>
  <summary>
    <i>$ <b>CodeChecker fixit --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker fixit [-h] [-l]
                         [--checker-name [CHECKER_NAME [CHECKER_NAME...]]]
                         [--file [FILE [FILE ...]]]
                         [--verbose {info,debug,debug_analyzer}]
                         folder [folder ...]

Some analyzers may suggest some automatic bugfixes. Most of the times these are
style issues which can be fixed easily. This command handles the listing and
application of these automatic fixes.

Besides the provided filter options you can pipe the JSON format output of
"CodeChecker cmd diff" command to filter automatic fixes only on new reports:
CodeChecker cmd diff -b dir1 -n dir2 -o json --new | CodeChecker fixit dir2

positional arguments:
  folder                The analysis result folder(s) containing analysis
                        results and fixits which should be applied.

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            List the available automatic fixes.
  -i, --interactive     Interactive selection of fixits to apply. Fixit items
                        are enumerated one by one and you may choose which
                        ones are to be applied. (default: False)
  --checker-name [CHECKER_NAME [CHECKER_NAME ...]]
                        Filter results by checker names. The checker name can
                        contain multiple * quantifiers which matches any number
                        of characters (zero or more). So for example
                        "*DeadStores" will match "deadcode.DeadStores".
                        (default: [])
  --file [FILE_PATH [FILE_PATH ...]]
                        Filter results by file path. The file path can contain
                        multiple * quantifiers which matches any number of
                        characters (zero or more). So if you have /a/x.cpp and
                        /a/y.cpp then "/a/*.cpp" selects both. (default: [])
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.
```
</details>

## `checkers`<a name="checkers"></a>

List the checkers available in the installed analyzers which can be used when
performing an analysis.

By default, `CodeChecker checkers` will list all checkers, one per each row,
providing a quick overview on which checkers are available in the analyzers.

<details>
  <summary>
    <i>$ <b>CodeChecker checkers --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker checkers [-h] [--analyzers ANALYZER [ANALYZER ...]]
                            [--details] [--profile {PROFILE/list}]
                            [--only-enabled | --only-disabled]
                            [-o {rows,table,csv,json}]
                            [--verbose {info,debug,debug_analyzer}]

Get the list of checkers available and their enabled status in the supported
analyzers.

optional arguments:
  -h, --help            show this help message and exit
  --analyzers ANALYZER [ANALYZER ...]
                        Show checkers only from the analyzers specified.
                        Currently supported analyzers are: clangsa, clang-
                        tidy.
  --details             Show details about the checker, such as description,
                        if available.
  --profile {PROFILE/list}
                        List checkers enabled by the selected profile.
                        'list' is a special option showing details about
                        profiles collectively.
  --guideline GUIDELINE [GUIDELINE ...]
                        List checkers that report on a specific guideline
                        rule. Here you can add the guideline name or the ID of
                        a rule. Without additional parameter, the available
                        guidelines and their corresponding rules will be
                        listed.
  --checker-config      Show checker configuration options for all
                        existing checkers supported by the analyzer.
                        These can be given to 'CodeChecker analyze
                        --checker-config'.
  --only-enabled        Show only the enabled checkers.
  --only-disabled       Show only the disabled checkers.
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        The format to list the applicable checkers as.
                        (default: rows)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.

The list of checkers that are enabled of disabled by default can be edited by
editing the file '.../config/checker_profile_map.json'.

Environment variables
------------------------------------------------
  CC_SEVERITY_MAP_FILE   Path of the checker-severity mapping config file.
                         Default: '<package>/config/checker_severity_map.json'
  CC_GUIDELINE_MAP_FILE  Path of the checker-guideline mapping config file.
                         Default: '<package>/config/checker_guideline_map.json'
  CC_PROFILE_MAP_FILE    Path of the checker-profile mapping config file.
                         Default: '<package>/config/checker_profile_map.json'
```
</details>

The list provided by default is formatted for easy machine and human
reading. Use the `--only-` options (`--only-enabled` and `--only-disabled`) to
filter the list if you wish to see just the enabled/disabled checkers.

A detailed view of the available checkers is available via `--details`. In the
*detailed view*, checker status, severity and description (if available) is
also printed.

A machine-readable `csv` or `json` output can be generated by supplying the
`--output csv` or `--output json` argument.

The _default_ list of enabled and disabled checkers can be altered by editing
`{INSTALL_DIR}/config/checker_profile_map.json`. Note, that this file is
overwritten when the package is reinstalled!

There are some coding guidelines which contain best practices on avoiding
common programming mistakes
([https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines](C++ Core Guidelines),
[https://wiki.sei.cmu.edu/confluence/display/seccode/SEI+CERT+Coding+Standards](SEI-CERT), etc.)
Many of these guideline rules can be checked by static analyzer tools. The
detailed output of `CodeChecker checkers` command contains information about
which checkers cover certain guideline rules. This mapping is given in
`<package>/config/checker_guideline_map.json` config file.

## <a name="analyzers"></a> 6. `analyzers` mode

List the available and supported analyzers installed on the system. This command
can be used to retrieve the to-be-used analyzers' install path and version
information.

By default, this command only lists the names of the available analyzers (with
respect to the environment CodeChecker is run in).

<details>
  <summary>
    <i>$ <b>CodeChecker analyzers --help</b> (click to expand)</i>
  </summary>

```
usage: CodeChecker analyzers [-h] [--all] [--details]
                             [--dump-config {clang-tidy,clangsa}]
                             [--analyzer-config {clang-tidy,clangsa}]
                             [-o {rows,table,csv,json}]
                             [--verbose {info,debug_analyzer,debug}]

Get the list of available and supported analyzers, querying their version and
actual binary executed.

optional arguments:
  -h, --help            show this help message and exit
  --all                 Show all supported analyzers, not just the available
                        ones.
  --details             Show details about the analyzers, not just their
                        names.
  --dump-config {clang-tidy,clangsa}
                        Dump the available checker options for the given
                        analyzer to the standard output. Currently only clang-
                        tidy supports this option. The output can be
                        redirected to a file named .clang-tidy. If this file
                        is placed to the project directory then the options
                        are applied to the files under that directory. This
                        config file can also be provided via 'CodeChecker
                        analyze' and 'CodeChecker check' commands. (default:
                        None)
  --analyzer-config {clang-tidy,clangsa}
                        Show analyzer configuration options. These can be
                        given to 'CodeChecker analyze --analyzer-config'.
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        Specify the format of the output list. (default: rows)
  --verbose {info,debug_analyzer,debug}
                        Set verbosity level.
```
</details>

A detailed view of the available analyzers is available via `--details`. In the
*detailed view*, version string and install path is also printed.

A machine-readable `csv` or `json` output can be generated by supplying the
`--output csv` or `--output json` argument.

# Configuring Clang version <a name="clang_version"></a>

_Clang_ and/or _Clang-Tidy_ must be available on your system before you can
run analysis on a project. CodeChecker automatically detects and uses the
latest available version in your `PATH`.

If you wish to use a custom `clang` or `clang-tidy` binary, e.g. because you
intend to use a specific version or a specific build, you need to configure
the installed CodeChecker package to use the appropriate binaries. Please edit
the configuration file
`~/codechecker/build/CodeChecker/config/package_layout.json`. In the
`runtime/analyzers` section, you must set the values, as shown below, to the
binaries you intend to use.

```json
"analyzers" : {
  "clangsa" : "/path/to/clang/bin/clang-8",
  "clang-tidy" : "/path/to/clang/bin/clang-tidy-8"
},
```

You can set the `CC_ANALYZERS_FROM_PATH` environment variable before running a
CodeChecker command to `yes` or `1` to enforce taking the analyzers from the
`PATH` instead of the given binaries. If this option is set you can also
configure the plugin directory of the Clang Static Analyzer by using the
`CC_CLANGSA_PLUGIN_DIR` environment variable.

Make sure that the required include paths are at the right place!
Clang based tools search by default for
[builtin-includes](https://clang.llvm.org/docs/LibTooling.html#builtin-includes)
in a path relative to the tool binary.
`$(dirname /path/to/tool)/../lib/clang/8.0.0/include`

# Suppressing False positives (source code comments for review status) <a name="source-code-comments"></a>

Source code comments can be used in the source files to change the review
status of a specific or all checker results found in a particular line of code.
Source code comment should be above the line where the defect was found, and
__no__ empty lines are allowed between the line with the bug and the source
code comment.

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

## Change review status of a specific checker result by using a substring of the checker name
There is no need to specify the whole checker name in the source code comment
like `deadcode.DeadStores`, because it will not be resilient to package name
changes. You are able to specify only a substring of the checker name for the
source code comment:
```cpp
void test() {
  int x;
  // codechecker_confirmed [DeadStores] suppress deadcode
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
