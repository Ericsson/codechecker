# Configuring the analyzers and their checkers

CodeChecker can acts as a driver for many separate **analyzer** tools like Clang
Static Analyzer, Clang Tidy or Cppcheck; and each analyzer supports many
different **checkers** (which are also called "checks" or "error types" etc. by
various tools). `CodeChecker analyze` accepts four command-line flags that can
be used to configure these:

* The flag `--analyzer-config <analyzer>:<option>=<value>` sets configuration
  options that affect a whole analyzer tool: for example specifying
  `--analyzer-config clangsa:mode=shallow` instructs `clangsa` (i.e. the
  Clang Static Analyzer) to use the `shallow` analysis mode (for a quicker,
  less accurate analysis).
* The flags `--enable <checker>` and `--disable <checker>` (which can be
  shortened to `-e` or `-d`) can enable or disable a checker or a group or
  profile that contains multiple checkers.
  *This sort of configuration is out of scope for this document, see the User
  Guide for information about toggling checkers.*
* The flag `--checker-config <analyzer>:<checker>:<option>=<value>` set
  configuration options that only affect a single checker: for example
  `--checker-config
  clang-tidy:bugprone-sizeof-expression:WarnOnSizeOfPointer=true`
  enables a part of the `bugprone-sizeof-expression` check that is not enabled
  by default.

The available configuration options can be listed with the following commands:
* `CodeChecker analyzers --analyzer-config <analyzer> --details` lists the
  options that can be passed to `--analyzer-config`.
* `CodeChecker checkers` lists the available checkers that can be enabled or
  disabled.
* `CodeChecker checkers --checker-config` lists the available checker options
  that can be passed to `--checker-config`.
By default `CodeChecker checkers` lists checkers or checker options from all
analyzers, but specifying the `--analyzers` option restricts this to one or more
analyzers: e.g. `CodeChecker checkers --analyzers clangsa clang-tidy` only lists
the checkers from `clangsa` and `clang-tidy`.

## Specific considerations for the Clang Static Analyzer

For the full documentation of the checkers and their options see the page
[Available Checkers](https://clang.llvm.org/docs/analyzer/checkers.html),
while the global analyzer options are documented at [Configuring the
Analyzer](https://clang.llvm.org/docs/analyzer/user-docs/Options.html).

CodeChecker does not expose the `debug` or hidden checkers through high-level
flags like `--enable` (because they are only relevant for developers of the
analyzer), use verbatim command-line arguments if you need enable them.

### Verbatim command-line arguments

In addition to the normal options offered by the analyzer itself, CodeChecker
implements the "magic" analyzer option `clangsa:cc-verbatim-args-file` which
forwards "raw" command-line arguments to the `clang` driver. The value of this
option should be the name of a file that contains all the arguments in a single
line. For example if the file `args.cfg` contains
```
-Dfoo=bar -Xclang -analyzer-max-loop -Xclang 10
```
then this can be passed to an analysis command as
```
CodeChecker analyze --analyzer-config clangsa:cc-verbatim-args-file=args.cfg \
        compile_commands.json

```
to inject a macro definition (`#define foo bar`) and specify that the analyzer
should simulate 10 iterations (instead of the default 4) within loops.

**Notes:**
* The contents of the args file are passed to the `clang` _driver_, which is a
  high-level GCC-like interface of clang. In this context, clang-specific flags
  (in particular the flags that influence the analyzer) and the corresponding
  values must be prefixed with `-Xclang` (as in the example) to ensure that the
  driver forwards them to the right place.
* Insted of `--analyzer-config clangsa:cc-verbatim-args-file=<FILE>`, older
  versions of CodeChecker used a standalone flag `--saargs <FILE>` which is now
  deprecated and will be removed in the future.

### Report validation via the Z3 Theorem Prover

The [Z3 Theorem Prover](https://github.com/Z3Prover/z3) from Microsoft Research
is an open source constraint solver tool, which can be optionally used by the
Clang Static Analyzer to improve the quality of results. This feature is only
available if the `clang` binary was built with the `LLVM_ENABLE_Z3_SOLVER=ON`
compile-time option.

If the Z3 Prover is available, then adding `--z3-refutation on` to the
`CodeChecker analyze` command enables _Z3 refutation_ mode which uses Z3 to
review the results found by the analyzer and discard results that are logically
inconsistent (according to the more accurate constraint tracking of Z3).

**Notes:**
* For more information about Z3 refutation, see also [the report by Mikhail
  Ramalho](https://lists.llvm.org/pipermail/cfe-dev/2018-August/058912.html)
  who developed this feature in 2018.
* This Z3 refutation mode (which is also known as Z3 validation and Z3
  crosschecking) should not be confused with the "Z3 as the constraint solver"
  mode where Z3 completely replaces the builtin constraint modeling of the
  analyzer. Unfortunately this "Z3 as constraint solver" mode is a failed
  experiment: it produces many crashes, increases the runtime by an order of
  magnitude and there are no plans to improve it in the foreseeable future.
  Passing `--z3 on` to `CodeChecker analyze` enables this broken mode.
* If the `clang` used by CodeChecker does not support Z3, then CodeChecker does
  not recognize the Z3-specific options, which produces confusing errors like
  `error: argument input: File doesn't exist: <SOMEPATH>/on` (because the value
  `on` is parsed as an input file name).

## Specific considerations for Clang-Tidy

The checks and config options provided by Clang-Tidy are described within the
[Clang-Tidy Documentation](https://clang.llvm.org/extra/clang-tidy/index.html).

### Using Clang-Tidy configuration files

When Clang-Tidy is executed without an explicit configuration, it will
implicitly load configuration from files named `.clang-tidy`: for each analyzed
source file it will load configuration from the file named `.clang-tidy`
located in the closest enclosing directory of that source file.

When Clang-Tidy is executed by CodeChecker, the default behavior is that
CodeChecker runs `clang-tidy --config=...` to forward the configuration
specified in CodeChecker (the enabled checkers + analyzer and checker options)
and therefore the `.clang-tidy` files are ignored in this default workflow.

However, the config forwarding can be disabled by the "magic" analyzer option
`clang-tidy:take-config-from-directory=true`; when this is specified,
Clang-Tidy will read configuration from the `.clang-tidy` files; but
configuration specified in CodeChecker (enabled checkers and profiles, analyzer
and checker options) **will be ignored by Clang-Tidy!**

The `.clang-tidy` files should be specified in the YAML format, for example:

```yaml
---
Checks:          'clang-diagnostic-*,clang-analyzer-*'
WarningsAsErrors: ''
HeaderFilterRegex: ''
AnalyzeTemporaryDtors: false
CheckOptions:
  - key:             google-readability-braces-around-statements.ShortStatementLines
    value:           '1'
  - key:             modernize-loop-convert.MaxCopySize
    value:           '16'
  - key:             modernize-loop-convert.NamingStyle
    value:           CamelCase
  - key:             modernize-use-nullptr.NullMacros
    value:           'NULL'
...
```

Note that JSON is a subset of YAML (if we ignore a few minor differences), so
configuration specified with JSON syntax is also accepted:

```json
{
  "Checks": "clang-diagnostic-*,clang-analyzer-*",
  "WarningsAsErrors": "",
  "HeaderFilterRegex": "",
  "AnalyzeTemporaryDtors": false,
  "CheckOptions": [
    {
      "key": "google-readability-braces-around-statements.ShortStatementLines",
      "value": "1"
    },
    {
      "key": "modernize-loop-convert.MaxCopySize",
      "value": "16"
    },
    {
      "key": "modernize-loop-convert.NamingStyle",
      "value": "CamelCase"
    },
    {
      "key": "modernize-use-nullptr.NullMacros",
      "value": "NULL"
    }
  ]
}
```

### Verbatim command-line arguments for Clang-Tidy

[Verbatim command-line arguments](#verbatim-command-line-arguments) are also
supported for Clang-Tidy via the "magic" analyzer option
`clang-tidy:cc-verbatim-args-file`. The value of this
option should be the name of a file that contains all the arguments in a single
line. For example a configuration file that looks like
```
-config="{ ... single line with lots of JSON .. }"
```
can be used to directly specify the Clang-Tidy configuration.

**Note:**
* Instead of `--analyzer-config clang-tidy:cc-verbatim-args-file=<FILE>`, older
  versions of CodeChecker used a standalone flag `--tidyargs <FILE>` which is
  now deprecated and will be removed in the future.

## Specific considersations for Cppcheck

As of CodeChecker 6.20 analysis via Cppcheck is supported and the following
options are recognized:
* `cppcheck:addons` A list of Cppcheck addon files.
* `cppcheck:libraries` A list of Cppcheck library definition files.
* `cppcheck:platform` The platform configuration .xml file.
* `cppcheck:inconclusive` Enable inconclusive reports.

Please note that multiple addons and libraries must be specified with separate
uses of `--analyzer-config` (as in the example).

Example invocation:
``` shell
CodeChecker check -l ./compile_commands.json \
  --analyzers cppcheck \ # Run Cppcheck analyzer only
  -e Cppcheck-missingOverride \ # enable the missingOverride Cppcheck check
  -d Cppcheck-virtualCallInConstructor \ # disable the virtualCallInConstructor check
  --analyzer-config cppcheck:addons=../cppcheck/addons/misc.py \ # enable the misc checks
  --analyzer-config cppcheck:addons=../cppcheck/addons/cert.py \ # enable cert cheks
  --analyzer-config cppcheck:libraries=../cppcheck/cfg/zlib.cfg \ # add zlib definitons
  --analyzer-config cppcheck:libraries=../cppcheck/cfg/gnu.cfg \ # add gnu definitions
  --analyzer-config cppcheck:inconclusive=true \ # allow inconclusive reports
  -o ./reports
```
### Notes and limitations

* The whole program analysis feature of Cppcheck is not supported. Cppcheck is
  invoked for every item in the provided compilation database.
  * The `cppcheck-unususedFunction` checker of Cppcheck is always disabled by default.
  * The CTU functionality of Cppcheck is not supported.
* The severity categorizations are only provided for the built in checkers.
  Addon checkers can be used, but their reports severity will be displayed as
  `Unspecified`.
* The Cppcheck categorization of checkers is not yet introduced into the
  Cppcheck label [file](../../config/labels/analyzers/cppcheck.json). To enable
  a whole category, each individual checker needs to be enabled with the
  `--enable` flag.
* All Cppcheck Errors and Warnings are enabled by default.
* Cppcheck addon support is limited in terms of configuration. Checkers
  residing in Cppcheck addons cannot be listed through the Cppcheck command
  line interface. Because of this limitation, these checkers cannot be
  disabled. Right now the only way to silence a report is to suppress them
  after the analysis. These addon checkers also cannot be listed with the
  `CodeChecker checkers` command.
* If not configured, `Native` platform will be assumed for the analyzed
  compilation database (i.e. the type sizes of the host system are used). No
  platform translation will occur by CodeChecker. If another one is needed,
  please provide a platform file with the correct bit lengths.
* To reach maximum compatibility with the existing CodeChecker invocation,
  Cppcheck is invoked with the `--enable=all` parameter, and all non-needed
  checkers are passed in as `--suppress=<checker>`.
* Due to legal reasons, no MISRA rule texts are supplied.
* Cppcheck only supports a limited number of platforms. Custom bit lengths can
  be specified with a platform file.

An example platform file from the Cppcheck manual:

``` xml
<?xml version="1"?>
<platform>
  <char_bit>8</char_bit>
  <default-sign>signed</default-sign>
  <sizeof>
    <short>2</short>
    <int>4</int>
    <long>4</long>
    <long-long>8</long-long>
    <float>4</float>
    <double>8</double>
    <long-double>12</long-double>
    <pointer>4</pointer>
    <size_t>4</size_t>
    <wchar_t>2</wchar_t>
  </sizeof>
</platform>
```

## Specific considerations for the GCC Static Analyzer

As of CodeChecker 6.23, Codechecker can now execute the GCC Static Analyzer.
The minimum version of GCC we support is 13.0.0. If you are having trouble with
making CodeChecker find the appropriate binary, try using the `CC_ANALYZER_BIN`
environmental variable (see `CodeChecker analyze --help`).

Example invocation:
``` shell
CodeChecker check -l ./compile_commands.json \
  --analyzers gcc \ # Run GCC analyzer only
  -e gcc \ # enable all checkers starting with "gcc"
  -d gcc-double-free \ # disable gcc-double-free
  -o ./reports
```

### Notes and limitations
* Currently, we don't support configuring the GCC Static analyzer through
  CodeChecker. The _overwhelming_ majority of these configurations are only
  recommended for developers -- but we will keep an eye out if this ever
  changes.
* As of now, we are not aware of any checker-specific configuration.
* Up to and including GCC version 13, the analyzer is only recommended for C
  code.
* Taint checkers are still in the early phases in development as of GCC-13, so
  they should only be enabled for experimentation.

## Configuring the FB-Infer Analyzer

As of CodeChecker 6.23, Codechecker can now execute the Facebook Infer Analyzer.
The minimum version of Infer we support is 1.1.0.

Example invocation:
``` shell
CodeChecker check -l ./compile_commands.json \
  --analyzers infer \ # Run Infer analyzer only
  -e infer \ # enable all checkers starting with "infer"
  -d infer-expensive-loop-invariant-call \ # disable infer-expensive-loop-invariant-call
  -o ./reports
```

### Notes and limitations
* Currently, we don't support configuring the Facebook Infer analyzer through
  CodeChecker. The _overwhelming_ majority of these configurations are only
  recommended for developers -- but we will keep an eye out if this ever
  changes.
* Currently only static analysis can be executed. Meaning that it analyzes each
  file separately and not the whole project as one.