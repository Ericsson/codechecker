# Configuring Clang Static Analyzer and checkers

## Analyzer Configuration <a name="analyzer-configuration"></a>

The analysis can be configured using analyzer wide configuration parameters.
These parameters may have effect on the whole analysis, affecting the result of
all checkers.

Listing the available configuration options:
`CodeChecker analyzers --analyzer-config clangsa --details`

Setting analyzer configuration options:
`CodeChecker analyze --analyzer-config <key=value>`

The descriptions of these global analyzer options are also available on the
[Configuring the
Analyzer](https://clang.llvm.org/docs/analyzer/user-docs/Options.html) page of
the Clang Static Analyzer Documentation.

See also ``CodeChecker analyze --help`` for more specific applications, e.g.
alternatives for the old deprecated ``--saargs`` flag.

## Checker Configuration <a name="checker-configuration"></a>

Clang Static Analyzer checkers can be enabled and disabled with the flags
`CodeChecker analyze --enable <checker_name> --disable <checker_name>`. The
checkers can be listed with `CodeChecker checkers --analyzers clangsa` and
their full documentation can be found at the [Available
Checkers](https://clang.llvm.org/docs/analyzer/checkers.html) page.

Note that these high-level CodeChecker operations hide some internal (debug or
modeling) checkers that are only relevant for the developers of the Clang
Static Analyzer.

Some checkers can be customized using checker specific configuration options,
which can be set by `CodeChecker analyze --checker-config
clangsa:<option-name>=<value>`. These options are documented on the [Available
Checkers](https://clang.llvm.org/docs/analyzer/checkers.html) page (within the
description of the corresponding checker) and they can be listed with the command
`CodeChecker checkers --checker-config`.

## Clang Static Analyzer Special Configuration Options

In special cases, when the checker and analyzer configurability that is provided
by CodeChecker is not enough, the Clang Static analyzer configuration can be
extended through the `--saargs` analysis option. The content of the saargs file
are forwarded as arguments without modification to the Clang Static Analyzer:
```
CodeChecker analyze --saargs static_analyzer.cfg
```

In the `static_analyzer.cfg` file various static analyzer and checker related
configuration options can be configured like this:
```
-Xclang -analyzer-config -Xclang unix.Malloc:Optimistic=true -Xclang -analyzer-max-loop -Xclang 20
```
__Before every configuration option '-Xclang' argument should be written and
all the configuration options sould be in one line! __

In the `static_analyzer.cfg` example file we set a checker specific
configuration option `unix.Malloc:Optimistic=true` for the `unix.Malloc`
checker and a static analyzer configuration option `analyzer-max-loop` (the
maximum number of times the analyzer will go through a loop, the default
value is 4).

### Enabling developer checkers

You cannot enable/disable developer checkers in CodeChecker using the `--enable`
or `--disable` flags.

These (debug and modeling) checkers should not be used normally. They are
typically used by ClangSA developers debug the analysis or to write test cases.
These checkers can be listed by `clang -cc1 -analyzer-checker-help-developer`.

If they are needed, they can be switched on using the following command
`CodeChecker analyzer --saarg saarg.config`, where the content of saarg.config
is for example `-Xclang -analyzer-checker=debug.ExprInspection`.

## Z3 Theorem Prover
The _Clang Static Analyzer_ supports using the
[Z3 Theorem Prover](https://github.com/Z3Prover/z3) from Microsoft Research as
an external constraint solver. This allows reasoning over more complex queries,
but performance is expected to be **15-20 times** slower than the default
range-based constraint solver engine.

To enable the Z3 solver backend, Clang must be built with the
`LLVM_ENABLE_Z3_SOLVER=ON` compile-time option (for versions earlier than
**9.0**, `CLANG_ANALYZER_BUILD_Z3=ON` must be used instead!), and the
`-Xanalyzer -analyzer-constraints=z3` arguments passed at runtime. CodeChecker
will automatically detect whether Clang was built with this option and you
don't have to pass these arguments to the analyzer command itself when using
CodeChecker, you just have to run the `CodeChecker analyze` command with the
`--z3` option.

You can read more about Z3 Theorem Prover
[here](https://github.com/Z3Prover/z3/wiki).

## Use Z3 SMT Solver to validate reports
Z3 SMT Solver can reduce the number of false positive bugs reported to the user
by the Clang Static Analyzer (CSA), without introducing too much overhead to
the analysis.

The bug refutation in the static analyzer is disabled by default and it’s
hidden behind the flag `--crosscheck-with-z3`. Once the user has a version of
clang built with Z3, the bug refutation can be enabled by passing
`--analyzer-config clangsa:crosscheck-with-z3=true` when calling the clang static
analyzer. CodeChecker will automatically detect that the Clang was built with
this option and you don't have to pass these arguments to the analyzer command
itself when using CodeChecker, you just have to run the CodeChecker analyze
command with the `--z3-refutation` option.

You can read more about refutation with the Z3 SMT Solver
[here](https://docs.google.com/document/d/1-HEblH92VxdxDp04vDKjFa4_ZL9l2oPVLFtQUfLKSOo/).

# Configuring Clang-Tidy

## Configuring the analyzer and checkers

You can configure the clang-tidy analyzer and its checkers through CodeChecker
with the `--analyzer-config` and the `--checker-config` flags of `CodeChecker
analyze/check` commands as described in sections [Analyzer
Configuration](#analyzer-configuration) and [Checker
Configuration](#checker-configuration).


## Using Clang-Tidy configuration files

If you want to control the configuration of clang-tidy from the `.clang-tidy`
configuration files (instead of the CodeChecker command line)  you can use the
`clang-tidy:take-config-from-directory=true` option. It will skip setting the
checkers and checker configuration from CodeChecker (even if a profile was
specified).

Then __clang-tidy__ will attempt to read configuration for each analyzed source file
from a `.clang-tidy` file located in the closest parent directory of the
analyzed source file.

So by executing `CodeChecker analyze compile_commands.json -o ./reports --analyzer-config 'clang-tidy:take-config-from-directory=true'`, CodeChecker will generate a clang-tidy command which will NOT 
contain the -checks option at all so your .clang-tidy file will take precedence.

The `.clang-tidy` configuration file can be in JSON or YAML format.

JSON:
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

or the same configuration in YAML format:

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

## Using tidyargs option in CodeChecker

The `--tidyargs` analysis argument can be used to forward configuration options
through CodeChecker to the clang-tidy analyzer.
```
CodeChecker analyze --tidyargs tidy_analyzer.cfg
```
Where the ```tidy_analyzer.cfg``` config file content looks like this where the
configuration arguments (json in this case) should be in one line :

```
-config="{ "Checks": "clang-diagnostic-*,clang-analyzer-*", "WarningsAsErrors": "", "HeaderFilterRegex": "", "AnalyzeTemporaryDtors": false, "CheckOptions": [ { "key": "google-readability-braces-around-statements.ShortStatementLines", "value": "1" }, { "key": "modernize-loop-convert.MaxCopySize", "value": "16" }, { "key": "modernize-loop-convert.NamingStyle", "value": "CamelCase" }, { "key": "modernize-use-nullptr.NullMacros", "value": "NULL" } ] }"
```

# Configuring Cppcheck

As of CodeChecker 6.20, Codechecker can now execute the Cppcheck analyzer.

## Analyzer Configuration

The Cppcheck analyzer can be configured with --analyzer-config cppcheck:* parameters.

The supported analyzer configuration items can be listed with `CodeChecker analyzers --analyzer-config cppcheck --details`

As of CodeChecker 6.20, the following options are supported:

* `cppcheck:addons` A list of Cppcheck addon files.
* `cppcheck:libraries` A list of Cppcheck library definition files.
* `cppcheck:platform` The platform configuration .xml file.
* `cppcheck:inconclusive` Enable inconclusive reports.

Please note that for addons and libraries, multiple items can be specified in the following format: `--analyzer-config cppcheck:addons <addon.py> --analyzer-config cppcheck:addons <addon2.py>`.

Cppcheck only supports a limited number of platforms. Custom bit lengths can be specified with a platform file.

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

## Limitations

The following limitations need to be considered when using Cppcheck:

* The whole program analysis feature of Cppcheck is not supported. Cppcheck is invoked for every item in the provided compilation database.
  * The `cppcheck-unususedFunction` checker of Cppcheck is always disabled by default.
  * The CTU functionality of Cppcheck is not supported.
* The severity categorizations are only provided for the built in checkers. Addon checkers can be used, but their reports severity will be displayed as `Unspecified`.
* The Cppcheck categorization of checkers is not yet introduced into the Cppcheck label [file](../../config/labels/analyzers/cppcheck.json). To enable a whole category, each individual checker needs to be enabled with the `--enable` flag.
* All Cppcheck Errors and Warnings are enabled by default.
* Cppcheck addon support is limited in terms of configuration. Checkers residing in Cppcheck addons cannot be listed through the Cppcheck commandline interface. Because of this limitation, these checkers cannot be disabled. Right now the only way to silence a report is to suppress them after the analysis. These addon checkers also cannot be listed with the `CodeChecker checkers` command.
* If not configured, `Native` platform will be assumed for the analyzed compilation database (i.e. the type sizes of the host system are used). No platform translation will occur by CodeChecker. If another one is needed, please provide a platform file with the correct bit lengths.
* To reach maximum compatibility with the existing CodeChecker invocation, Cppcheck is invoked with the `--enable=all` parameter, and all non-needed checkers are passed in as `--suppress=<checker>`.
* Due to legal reasons, no MISRA rule texts are supplied.


## Example invocation
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

# Configuring the GCC Static Analyzer

As of CodeChecker 6.23, Codechecker can now execute the GCC Static Analyzer.
The minimum version of GCC we support is 13.0.0. If you are having trouble with
making CodeChecker find the appropriate binary, try using the `CC_ANALYZER_BIN`
environmental variable (see `CodeChecker analyze --help`).

## Analyzer Configuration

Currently, we don't support configuring the GCC Static analyzer through
CodeChecker. The _overwhelming_ majority of these configurations are only
recommended for developers -- but we will keep an eye out if this ever changes.

As of now, we are not aware of any configurations for checkers.

## Limitations

Up to and including GCC version 13, the analyzer is only recommended for C
code.

Taint checkers are still in the early phases in development as of GCC-13, so
they should only be enabled for experimentation.

## Example invocation

``` shell
CodeChecker check -l ./compile_commands.json \
  --analyzers gcc \ # Run GCC analyzer only
  -e gcc \ # enable all checkers starting with "gcc"
  -d gcc-double-free \ # disable gcc-double-free
  -o ./reports
```

# Configuring the FB-Infer Analyzer

As of CodeChecker 6.23, Codechecker can now execute the Facebook Infer Analyzer.
The minimum version of Infer we support is 1.1.0.

## Analyzer Configuration

Currently, we don't support configuring the Facebook Infer analyzer through
CodeChecker. The _overwhelming_ majority of these configurations are only
recommended for developers -- but we will keep an eye out if this ever changes.

## Limitations

Currently only static analysis can be executed. Meaning that it analyzes each
file separately and not the whole project as one.

## Example invocation

``` shell
CodeChecker check -l ./compile_commands.json \
  --analyzers infer \ # Run Infer analyzer only
  -e infer \ # enable all checkers starting with "infer"
  -d infer-expensive-loop-invariant-call \ # disable infer-expensive-loop-invariant-call
  -o ./reports
```