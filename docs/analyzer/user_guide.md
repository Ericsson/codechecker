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
        * [Taint analysis configuration](#taint)
        * [Statistical analysis mode](#statistical)
    * [`parse`](#parse)
        * [`JSON` format of `CodeChecker parse`](#json-format-of-codechecker-parse)
          * [Report object](#report-object)
          * [File object](#file-object)
          * [Range object](#range-object)
          * [SourceCodeComment object](#sourcecodecomment-object)
          * [BugPathEvent object](#bugpathevent-object)
          * [BugPathPosition object](#bugpathposition-object)
          * [MacroExpansion object](#macroexpansion-object)
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
                         [--report-hash {context-free,context-free-v2,diagnostic-message}]
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
                        parameter should be a python regular expression. If
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
  --report-hash {context-free,context-free-v2,diagnostic-message}
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
                        - diagnostic-message: context free hash with bug step
                        messages is used for ClangSA and Clang Tidy.
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
  --config CONFIG_FILE  Allow the configuration from an explicit configuration
                        file. The values configured in the config file will
                        overwrite the values set in the command line.
                        You can use any environment variable inside this file
                        and it will be expaneded.
                        For more information see the docs: https://github.com/
                        Ericsson/codechecker/tree/master/docs/config_file.md
                        (default: None)
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
                        --analyzer-config'. If the file at --tidyargs contains
                        a -config flag then those options extend these and
                        override "HeaderFilterRegex" if any. To use analyzer
                        configuration file in case of Clang Tidy (.clang-tidy)
                        use the 'clang-tidy:take-config-from-directory=true'
                        option. It will skip setting the '-checks' parameter
                        of the clang-tidy binary. (default: ['clang-
                        tidy:HeaderFilterRegex=.*'])
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

  Checker labels
  ------------------------------------------------
  In CodeChecker there is a manual grouping of checkers. These groups are
  determined by labels. The collection of labels is found in
  config/labels directory. The goal of these labels is that you can
  enable or disable checkers by these labels. See the --label flag of
  "CodeChecker checkers" command.

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
                        group). Moreover, labels can also be used for
                        selecting checkers, for example profile:extreme or
                        severity:STYLE. See 'CodeChecker checkers --label' for
                        further details.
  -d checker/group/profile, --disable checker/group/profile
                        Set a checker (or checker group), profile or guideline
                        to BE PROHIBITED from use in the analysis. In case of
                        ambiguity the priority order is profile, guideline,
                        checker name (e.g. security means the profile, not the
                        checker group). Moreover, labels can also be used for
                        selecting checkers, for example profile:extreme or
                        severity:STYLE. See 'CodeChecker checkers --label' for
                        further details.
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

Environment variables for 'CodeChecker parse' command:

  CC_CHANGED_FILES       Path of changed files json from Gerrit. Use it when
                         generating gerrit output.
  CC_REPO_DIR            Root directory of the sources, i.e. the directory
                         where the repository was cloned. Use it when
                         generating gerrit output.
  CC_REPORT_URL          URL where the report can be found. Use it when
                         generating gerrit output.

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

- diagnostic-message:
  * Same as 'context-free-v2' (file name, checker message etc.)
  * 'bug step messages' from all events.

  Be careful with this hash because it can change easily for example on
  variable / function renames.

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

**Note**: If your compilation database log file contains relative paths you
have to make sure that you run the analysis command from the same directory
as the logger was run (i.e. that paths are relative to).

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
                           [--report-hash {context-free,context-free-v2,diagnostic-message}]
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
                        parameter should be a python regular expression. If
                        there is more than one compilation action for a
                        source, only the one is kept which matches the given
                        python regex. If more than one matches an error is
                        given. The whole compilation action text is searched
                        for match. (default: none)
  --report-hash {context-free,context-free-v2,diagnostic-message}
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
                        - diagnostic-message: context free hash with bug step
                        messages is used for ClangSA and Clang Tidy.
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
  --config CONFIG_FILE  Allow the configuration from an explicit configuration
                        file. The values configured in the config file will
                        overwrite the values set in the command line.
                        You can use any environment variable inside this file
                        and it will be expaneded.
                        For more information see the docs: https://github.com/
                        Ericsson/codechecker/tree/master/docs/config_file.md
                        (default: None)
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
                        --analyzer-config'. If the file at --tidyargs contains
                        a -config flag then those options extend these and
                        override "HeaderFilterRegex" if any. To use analyzer
                        configuration file in case of Clang Tidy (.clang-tidy)
                        use the 'clang-tidy:take-config-from-directory=true'
                        option. It will skip setting the '-checks' parameter
                        of the clang-tidy binary. (default: ['clang-
                        tidy:HeaderFilterRegex=.*'])
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
                        group). Moreover, labels can also be used for
                        selecting checkers, for example profile:extreme or
                        severity:STYLE. See 'CodeChecker checkers --label' for
                        further details.
  -d checker/group/profile, --disable checker/group/profile
                        Set a checker (or checker group or checker profile)
                        to BE PROHIBITED from use in the analysis. In case of
                        ambiguity the priority order is profile, guideline,
                        checker name (e.g. security means the profile, not the
                        checker group). Moreover, labels can also be used for
                        selecting checkers, for example profile:extreme or
                        severity:STYLE. See 'CodeChecker checkers --label' for
                        further details.
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
in the `{INSTALL_DIR}/config/labels` directory. Three built-in
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

Even specifying `--enable-all` will **NOT** enable checkers from the following
special checker groups: `alpha.`, `debug.`, `osx.`, `abseil-`, `android-`,
`darwin-`, `objc-`, `cppcoreguidelines-`, `fuchsia.`, `fuchsia-`, `hicpp-`,
`llvm-`, `llvmlibc-`, `google-`, `zircon`.

`osx.` checkers are only enabled if CodeChecker is run on a macOS machine.

`--enable-all` can further be fine-tuned with subsequent `--enable` and
`--disable` arguments, for example

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

### Taint analysis configuration <a name="taint"></a>

Taint analysis is used to detect bugs and potential security-related errors
caused by untrusted data sources.
An untrusted data source is usually an IO operation in code, often related to
the file-system, database, network, or environment variables.
Taint analysis works by defining operations that introduce tainted values
(`sources`), operations that cause taint to spread from tainted values
(`propagators`), and operations that are sensitive to tainted values (`sinks`).
Developers can also use an additional category of `filters` to express that some
operations sanitize tainted values, and after sanitization,
the value is trusted and safe to use.

Taint analysis can be used with the default configuration by enabling the
`alpha.security.taint.TaintPropagation` checker:
```sh
CodeChecker analyze -e alpha.security.taint.TaintPropagation
```

Taint analysis can be used with custom configuration by specifying the taint
configuration file as a checker-option in addition to enabling the
`alpha.security.taint.TaintPropagation` checker:
```sh
CodeChecer analyze \
  -e alpha.security.taint.TaintPropagation \
  --checker-config 'alpha.security.taint.TaintPropagation:Config=my-cutom-taint-config.yaml'
```

Taint analysis false positives can be handled by either using the warning
suppression via comments in the code (same as with other CodeChecker reports),
or by providing filter operations via a custom configuration file.

The default configuration options of taint analysis are documented in the
[checker's documentation](https://clang.llvm.org/docs/analyzer/checkers.html#alpha-security-taint-taintpropagation-c-c).

Clang SA's conceptual model of taint analysis and the checker's configuration
file format is documented in the [Taint Analysis Configuration docs](https://clang.llvm.org/docs/analyzer/user-docs/TaintAnalysisConfiguration.html).

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
usage: CodeChecker parse [-h] [--config CONFIG_FILE] [-t {plist}]
                         [-e {html,json,codeclimate,gerrit,baseline}]
                         [-o OUTPUT_PATH] [--suppress SUPPRESS]
                         [--export-source-suppress] [--print-steps]
                         [-i SKIPFILE]
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
  --config CONFIG_FILE  Allow the configuration from an explicit configuration
                        file. The values configured in the config file will
                        overwrite the values set in the command line.
                        You can use any environment variable inside this file
                        and it will be expaneded.
                        For more information see the docs: https://github.com/
                        Ericsson/codechecker/tree/master/docs/config_file.md
                        (default: None)
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
  -e {html,json,codeclimate,gerrit,baseline}, --export {html,json,codeclimate,gerrit,baseline}
                        Specify extra output format type.
                        'codeclimate' format can be used for Code Climate and
                        for GitLab integration. For more information see:
                        https://github.com/codeclimate/platform/blob/master/sp
                        ec/analyzers/SPEC.md#data-types
                        'baseline' output can be used to integrate CodeChecker
                        into your local workflow without using a CodeChecker
                        server. For more information see our usage guide.
                        (default: None)
  -o OUTPUT_PATH, --output OUTPUT_PATH
                        Store the output in the given file/folder. Note:
                        baseline files must have extension '.baseline'.

Environment variables
------------------------------------------------

  CC_CHANGED_FILES       Path of changed files json from Gerrit. Use it when
                         generating gerrit output.
  CC_REPO_DIR            Root directory of the sources, i.e. the directory
                         where the repository was cloned. Use it when
                         generating gerrit output.
  CC_REPORT_URL          URL where the report can be found. Use it when
                         generating gerrit output.

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

### `JSON` format of `CodeChecker parse`
Let's assume that we have the following source file:
```cpp
#define DIV(x, y) x / y

int foo(int p) {
  // codechecker_confirmed [core.DivideZero] This is a bug.
  return DIV(1, p);
}

int main() {
  return foo(0);
}
```

If we analyze this source file with `Clang Static Analyzer` and we call the
`CodeChecker parse` command with `json` output it will generate an output
similar to this one:

```json
{
  "version": 1,
  "reports": [
    {
      "analyzer_result_file_path": "/home/username/projects/dummy/reports/main.cpp_clangsa_13e0fcf9c1bae0de6da3cb3d0bf1f330.plist",
      "file": {
        "id": "/home/username/dummy/simple/main.cpp",
        "path": "projects/dummy/main.cpp",
        "original_path": "/home/username/projects/dummy/main.cpp"
      },
      "line": 5,
      "column": 12,
      "message": "Division by zero",
      "checker_name": "core.DivideZero",
      "severity": "HIGH",
      "report_hash": "7d5ccfef806a23b016a52d0df8f1f5d8",
      "analyzer_name": "clangsa",
      "category": "Logic error",
      "type": null,
      "source_code_comments": [
        {
          "checkers": [ "core.DivideZero" ],
          "message": "This is a bug.",
          "status": "confirmed",
          "line": "  // codechecker_confirmed [core.DivideZero] This is a bug.\n"
        }
      ],
      "review_status": "confirmed",
      "bug_path_events": [
        {
          "file": {
            "id": "/home/username/dummy/simple/main.cpp",
            "path": "projects/dummy/main.cpp",
            "original_path": "/home/username/projects/dummy/main.cpp"
          },
          "line": 9,
          "column": 14,
          "message": "Passing the value 0 via 1st parameter 'p'",
          "range": {
            "start_line": 9,
            "start_col": 14,
            "end_line": 9,
            "end_col": 14
          }
        },
        {
          "file": {
            "id": "/home/username/dummy/simple/main.cpp",
            "path": "projects/dummy/main.cpp",
            "original_path": "/home/username/projects/dummy/main.cpp"
          },
          "line": 9,
          "column": 10,
          "message": "Calling 'foo'",
          "range": {
            "start_line": 9,
            "start_col": 10,
            "end_line": 9,
            "end_col": 10
          }
        },
        {
          "file": {
            "id": "/home/username/dummy/simple/main.cpp",
            "path": "projects/dummy/main.cpp",
            "original_path": "/home/username/projects/dummy/main.cpp"
          },
          "line": 3,
          "column": 1,
          "message": "Entered call from 'main'",
          "range": {
            "start_line": 3,
            "start_col": 1,
            "end_line": 3,
            "end_col": 1
          }
        },
        {
          "file": {
            "id": "/home/username/dummy/simple/main.cpp",
            "path": "projects/dummy/main.cpp",
            "original_path": "/home/username/projects/dummy/main.cpp"
          },
          "line": 5,
          "column": 12,
          "message": "Division by zero",
          "range": {
            "start_line": 5,
            "start_col": 12,
            "end_line": 5,
            "end_col": 12
          }
        }
      ],
      "bug_path_positions": [
        {
          "range": {
            "start_line": 9,
            "start_col": 3,
            "end_line": 9,
            "end_col": 8
          },
          "file": {
            "id": "/home/username/dummy/simple/main.cpp",
            "path": "projects/dummy/main.cpp",
            "original_path": "/home/username/projects/dummy/main.cpp"
          }
        },
        {
          "range": {
            "start_line": 9,
            "start_col": 14,
            "end_line": 9,
            "end_col": 14
          },
          "file": {
            "id": "/home/username/dummy/simple/main.cpp",
            "path": "projects/dummy/main.cpp",
            "original_path": "/home/username/projects/dummy/main.cpp"
          }
        }
      ],
      "notes": [],
      "macro_expansions": [
        {
          "name": "DIV",
          "file": {
            "id": "/home/username/dummy/simple/main.cpp",
            "path": "projects/dummy/main.cpp",
            "original_path": "/home/username/projects/dummy/main.cpp"
          },
          "line": 5,
          "column": 10,
          "message": "1 / p",
          "range": {
            "start_line": 5,
            "start_col": 10,
            "end_line": 5,
            "end_col": 10
          }
        }
      ]
    }
  ]
}
```

- `version` (number): version number. If the format of the JSON output will
  change this value will be incremented too. Currently supported values: `1`.
- `reports` (list): list of [Report objects](#report-object).

#### Report object
- `file` (File): file where the report was found in. For more information
  [see](#file-object).
- `line` (number): line number.
- `column` (number): column number.
- `message` (str): message reported by the checker.
- `checker_name` (str): identifier of the rule (checker) that was evaluated
  to produce the result.
- `severity` (str | null): CodeChecker severity level (optional). Possible
values are: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `STYLE`, `UNSPECIFIED`.
- `report_hash` (str | null): bug identifier hash (optional).
- `analyzer_name` (str | null): analyzer name which reported the bug
  (optional).
- `analyzer_result_file_path` (str | null): analyzer result file path where
  the report comes from (optional).
- `category` (str | null): report category such as 'Logic error',
  'Code clone' etc. (optional)
- `type` (str): report type such as 'Division by zero',
  'Dereference of null pointer', etc. (optional).
- `source_code_comments` (list): list of CodeChecker source code comments. For
  more information [see](#sourcecodecomment-object).
- `review_status` (str): CodeChecker review status (default: 'unreviewed').
- `bug_path_events` (list[BugPathEvent]): list of bug path events. These events
will be shown as bug steps on the UI and CLI (e.g.:
`CodeChecker parse --print-steps`). For more information
[see](#bugpathevent-object).
- `bug_path_positions` (list): list of bug report points. These positions will
be used by the UI and if given, the UI will connect them with arrows. For more
information [see](#bugpathposition-object).
- `notes` (list[BugPathEvent]): list of notes. These events will be shown
on the UI and CLI (e.g.: `CodeChecker parse --print-steps`) separated from
bug steps and will hold useful information to understand the report. For more
information [see](#bugpathevent-object).
- `macro_expansions` (list): list of macro expansions. These events will be
shown on the UI and CLI (e.g.: `CodeChecker parse --print-steps`) separated
from bug steps and will hold useful information to understand macros in the bug
step. For more information [see](#macroexpansion-object).

#### File object
```json
{
  "id": "/home/username/dummy/simple/main.cpp",
  "path": "projects/dummy/main.cpp",
  "original_path": "/home/username/projects/dummy/main.cpp"
}
```

- `id` (str): unique identifier of the file object. Most of the cases it equals
with `original_path`.
- `path` (str): returns the trimmed version of the file path if leading paths
are removed previously (`--trim-path-prefix` option). Otherwise it will return
the same value as the `original_path`.
- `original_path` (str): original file path. Trimming the file path will not
modify this value.

#### Range object
```json
{
  "start_line": 8,
  "start_col": 14,
  "end_line": 8,
  "end_col": 14
}
```

- `start_line` (number): start line number.
- `start_col` (number): start column number.
- `end_line` (number): end line number.
- `end_col` (number): end column number.

#### SourceCodeComment object
```json
{
  "checkers": [ "core.DivideZero" ],
  "message": "This is a bug.",
  "status": "confirmed",
  "line": "  // codechecker_confirmed [core.DivideZero] This is a bug.\n"
}
```

- `checkers` (list[str]): list of checker names from the source code comment.
`all` is a special checker name and it indicates that the source code comment
is related to all results.
- `message` (str): source code comment message which will be shown on the UI
after storage.
- `status` (str): status of the source code comment. Possible values:
`unreviewed`, `suppress`, `false_positive`, `intentional`, `confirmed`.
- `line` (str): full line of the source code comment.

For more information [read](#source-code-comments).

#### BugPathEvent object
```json
{
  "file": {
    "id": "/home/username/dummy/simple/main.cpp",
    "path": "projects/dummy/main.cpp",
    "original_path": "/home/username/projects/dummy/main.cpp"
  },
  "line": 8,
  "column": 14,
  "message": "Passing the value 0 via 1st parameter 'p'",
  "range": {
    "start_line": 8,
    "start_col": 14,
    "end_line": 8,
    "end_col": 14
  }
}
```

- `file` (File): file where the event was found in. For more information
[see](#file-object).
- `line` (number): line number.
- `column` (number): column number.
- `message` (str): bug path event message.
- `range` (Range): more precise information about event location (optional).
For more information [see](#range-object).

#### BugPathPosition object
```json
{
  "range": {
    "start_line": 8,
    "start_col": 3,
    "end_line": 8,
    "end_col": 8
  },
  "file": {
    "id": "/home/username/dummy/simple/main.cpp",
    "path": "projects/dummy/main.cpp",
    "original_path": "/home/username/projects/dummy/main.cpp"
  },
}
```

- `file` (File): file where the position can be found in. For more information
[see](#file-object).
- `range` (Range): information about bug path position. For more information
[see](#range-object).

#### MacroExpansion object
```json
{
  "name": "DIV",
  "file": {
    "id": "/home/username/dummy/simple/main.cpp",
    "path": "projects/dummy/main.cpp",
    "original_path": "/home/username/projects/dummy/main.cpp"
  },
  "line": 5,
  "column": 10,
  "message": "1 / p",
  "range": {
    "start_line": 5,
    "start_col": 10,
    "end_line": 5,
    "end_col": 10
  }
}
```

- `name` (str): macro name which will be expanded.
- Same fields as `BugPathEvent` type:
  - `file` (File): file where the macro expansion was found in. For more
  information [see](#file-object).
  - `line` (number): line number.
  - `column` (number): column number.
  - `message` (str): expanded message.
  - `range` (Range | null): more precise information about event location
  (optional). For more information [see](#range-object).

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
                            [--details] [--label LABEL [LABEL ...]]
                            [--profile {PROFILE/list}]
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
  --details             Show details about the checker, such as status,
                        checker name, analyzer name, severity, guidelines and
                        description. Status shows if the checker is enabled
                        besides the given labels. If the labels don't trigger
                        a checker then the status is determined by the
                        analyzer tool.
  --label [LABEL]       Filter checkers that are attached the given label. The
                        format of a label is <label>:<value>. If no argument
                        is given then available labels are listed. If only
                        <label> is given then available values are listed.
  --profile [PROFILE]   List checkers enabled by the selected profile. If no
                        argument is given then available profiles are listed.
  --guideline [GUIDELINE]
                        List checkers that report on a specific guideline.
                        Without additional parameter, the available guidelines
                        and their corresponding rules will be listed.
  --severity [SEVERITY]
                        List checkers with the given severity. Make sure to
                        indicate severity in capitals (e.g. HIGH, MEDIUM,
                        etc.) If no argument is given then available
                        severities are listed.
  --checker-config      Show checker configuration options for all
                        existing checkers supported by the analyzer.
                        These can be given to 'CodeChecker analyze
                        --checker-config'.
  --only-enabled        DEPRECATED. Show only the enabled checkers.
  --only-disabled       DEPRECATED. Show only the disabled checkers.
  -o {rows,table,csv,json}, --output {rows,table,csv,json}
                        The format to list the applicable checkers as.
                        (default: rows)
  --verbose {info,debug,debug_analyzer}
                        Set verbosity level.

The list of checkers that are enabled or disabled by default can be edited by
editing "profile:default" labels in the file '{}'.

Example scenario: List checkers by labels
-----------------------------------------
List checkers in "sensitive" profile:
    CodeChecker checkers --label profile:sensitive
    CodeChecker checkers --profile sensitive

List checkers in "HIGH" severity:
    CodeChecker checkers --label severity:HIGH
    CodeChecker checkers --severity HIGH

List checkers covering str34-c SEI-CERT rule:
    CodeChecker checkers --label sei-cert:str-34-c
    CodeChecker checkers --guideline sei-cert:str34-c

List checkers covering all SEI-CERT rules:
    CodeChecker checkers --label guideline:sei-cert
    CodeChecker checkers --guideline sei-cert

List available profiles, guidelines and severities:
    CodeChecker checkers --profile
    CodeChecker checkers --guideline
    CodeChecker checkers --severity

List labels and their available values:
    CodeChecker checkers --label
    CodeChecker checkers --label severity
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
config files in `{INSTALL_DIR}/config/labels`. Note, that this directory is
overwritten when the package is reinstalled!

There are some coding guidelines which contain best practices on avoiding
common programming mistakes
([https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines](C++ Core Guidelines),
[https://wiki.sei.cmu.edu/confluence/display/seccode/SEI+CERT+Coding+Standards](SEI-CERT), etc.)
Many of these guideline rules can be checked by static analyzer tools. The
detailed output of `CodeChecker checkers` command contains information about
which checkers cover certain guideline rules. This mapping is given in the
config files of `<package>/config/labels` directory.

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

## Change review status for multiple checker results in the same line
You can change multiple checker reports with a single source code comment:

```cpp
void test() {
  // codechecker_confirmed [clang-diagnostic-division-by-zero, core.DivideZero] These are real problems.
  int x = 1 / 0;
}
```

The limitation of this format is that you can't use separate status or message
for checkers. To solve this problem you can use one of the following format:

```cpp
void test_simple() {
  // codechecker_confirmed [clang-diagnostic-division-by-zero, core.DivideZero] This is a real bug.
  // codechecker_intentional [clang-diagnostic-unused-variable] This is not a bug.
  int x = 1 / 0;
}

void test_simple() {
  /**
   * codechecker_intentional [core.DivideZero] This is a real bug.
   * codechecker_confirmed [clang-diagnostic-unused-variable] This is not a bug.
   */
  int x = 1 / 0;
}
```

**WARNING**: using multiple source code comments for the same checker is not
supported and will give you an error:

```cpp
void testError1() {
  // codechecker_confirmed [clang-diagnostic-unused-variable] These are real problems.
  // codechecker_intentional [clang-diagnostic-unused-variable] This is not a bug.
  int x = 1 / 0;
}

void testError2() {
  // codechecker_confirmed [all] These are real problems.
  // codechecker_intentional [clang-diagnostic-unused-variable] This is not a bug.
  int x = 1 / 0;
}
```
