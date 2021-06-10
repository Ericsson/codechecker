# Configure Clang Static Analyzer and checkers

Analyzer configuration can be done through the `--saargs` analysis option which
forwards arguments without modification to the Clang Static Analyzer:
```
CodeChecker analyze --saargs static_analyzer.cfg
```

In the `static_analyzer.cfg` file various static analyzer and checker related
configuration options can be configured like this:
```
-Xclang -analyzer-config -Xclang unix.Malloc:Optimistic=true -Xclang -analyzer-max-loop -Xclang 20
```
__Before every configuration option '-Xclang' argument should be written and
all the configuration options sould be in one line!__

In the `static_analyzer.cfg` example file we set a checker specific
configuration option `unix.Malloc:Optimistic=true` for the `unix.Malloc`
checker and a static analyzer configuration option `analyzer-max-loop` (the
maximum number of times the analyzer will go through a loop, the default
value is 4).

## Checker specific configuration options  
This is not a comprehensive list view checker
[documentation or implementation](https://github.com/llvm-mirror/clang/tree/master/lib/StaticAnalyzer/Checkers)
for available configuration options:

| checker name | configuration option           | default value | available values | description                                                                            |
|--------------|--------------------------------|---------------|------------------|----------------------------------------------------------------------------------------|
| nullability  | NoDiagnoseCallsToSystemHeaders | false         | true/false       | If true, the checker will not diagnose nullability issues for calls to system headers. |
| unix.Malloc  | Optimistic                     | false         | true/false       |                                                                                        |


## Clang Static Analyzer configuration options
This is not a comprehesive list, check out the
[clang static analyzer documentation](https://github.com/llvm-mirror/clang/tree/master/docs)
or source code for more details about the configuration options.

| configuration option                  | default value     | available values                         | description                                                                                         |
|---------------------------------------|-------------------|------------------------------------------|-----------------------------------------------------------------------------------------------------|
| analyzer-max-loop                     | 4                 |                                          |                                                                                                     |
| inline-lambdas                        | true              |                                          |                                                                                                     |
| ipa                                   | dynamic-bifurcate |                                          | [inter procedural analysis](https://github.com/llvm-mirror/clang/blob/master/docs/analyzer/IPA.txt) |
| ipa-always-inline-size                | 3                 |                                          |                                                                                                     |
| mode                                  | deep              | deep, shallow                            |                                                                                                     |
| max-inlinable-size                    | 100               |                                          | 100 for deep mode, 4 for shallow                                                                    |
| max-nodes                             | 225000            |                                          | 22500 for deep, 75000 for shallow, maximum number of nodes for top level functions                  |
| unroll-loops                          | false             | true/false                               |                                                                                                     |
| widen-loops                           | false             | true/false                               |                                                                                                     |
| suppress-null-return-paths            | false             |                                          |                                                                                                     |
| c++-inlining                          | constructors      | constructors, destructors, none, methods | [inlining options](https://github.com/llvm-mirror/clang/blob/master/docs/analyzer/IPA.txt)          |
| leak-diagnostics-reference-allocation | false             | true/false                               |                                                                                                     |
| max-times-inline-large                | 32                |                                          |                                                                                                     |
| region-store-small-struct-limit       | 2                 |                                          |                                                                                                     |
| path-diagnostics-alternate            | false             | true/false                               |                                                                                                     |
| report-in-main-source-file            | true              | true/false                               |                                                                                                     |
| min-cfg-size-treat-functions-as-large | 14                |                                          |                                                                                                     |
| cfg-conditional-static-initializers   | true              |                                          |                                                                                                     |
| cfg-implicit-dtors                    | true              | true/false                               |                                                                                                     |
| cfg-lifetime                          | false             | true/false                               |                                                                                                     |
| cfg-loopexit                          | false             | true/false                               |                                                                                                     |
| cfg-temporary-dtors                   | false             | true/false                               |                                                                                                     |
| faux-bodies                           | true              | true/false                               |                                                                                                     |
| graph-trim-interval                   | 1000              |                                          |                                                                                                     |


## Z3 Theorem Prover
The static analyzer supports using the
[Z3 Theorem Prover](https://github.com/Z3Prover/z3) from Microsoft Research as
an external constraint solver. This allows reasoning over more complex queries,
but performance is `~15x` slower than the default range-based constraint
solver. To enable the Z3 solver backend, Clang must be built with the
`CLANG_ANALYZER_BUILD_Z3=ON` option, and the
`-Xanalyzer -analyzer-constraints=z3` arguments passed at runtime. CodeChecker
will automatically detect that the Clang was built with this option and you
don't have to pass these arguments to the analyzer command itself when using
CodeChecker, you just have to run the CodeChecker analyze command with the
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

# Configure Clang tidy checkers

## Using Clang tidy configuration files

__clang-tidy__ attempts to read configuration for each analyzed source file
from a `.clang-tidy` file located in the closest parent directory of the
analyzed source file.

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
