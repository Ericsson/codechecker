# Compilation Database Transformer

Table of Contents
=================
* [Compilation commands](#compilation-commands)
* [Building](#building)
* [Usage](#usage)
  * [Make Clang compatible compilation database](#make-clang-compatible-compilation-database)
  * [Execute actions and check result](#execute-actions-and-check-result)
* [Log Parser Heuristics](#log-parser-heuristics)
  * [BuildAction parsing](#buildaction-parsing)
  * [Compiler detection](#compiler-detection)
  * [Gcc2Clang](#gcc2clang)
     * [Replace](#replace)
     * [Ignore specific compiler flags](#ignore-specific-compiler-flags)
     * [Ignore if the original compiler is gcc](#ignore-if-the-original-compiler-is-gcc)
     * [Ignore flags with parameters](#ignore-flags-with-parameters)
  * [Extend entries with response files](#extend-entries-with-response-files)
  * [Skip specific BuildActions](#skip-specific-buildactions)
  * [BuildAction uniqueing](#buildaction-uniqueing)
     * [Uniqueing kinds](#uniqueing-kinds)

## Compilation commands
This tool is intended to be used as a utility for making manipulation and transformation of compilation command databases. A compilation database is a list of compilation-actions needed to build a project. Compilation databases use JSON format, and conventionally named `compile_commands.json`. A compilation database has the following general format for each entry in the list of actions:
```
[
...
    {
        "directory": "<working directory of the action>",
        "command": "<the shell invocation used to execute the action>",
        "file": "<the source file of the action>",
    },
...
]
```

## Building
```
make venv
source venv/bin/activate

make package
```

## Usage
Currently the most basic usage is to invoke the `ccdb-tool` inside the `venv` virtualenv.

### Make Clang compatible compilation database
```
ccdb-tool clangify --input compile_commands.json --output compatible_comile_commands.json
```
Alternatively you can use feed input on the standard input, and expect output on the standard output as well.
```
cat compile_commands.json | ccdb-tool clangify > compatible_comile_commands.json
```

### Execute actions and check result 
```
ccdb-tool check --input compile_commands.json --output results.json
```
Alternatively you can use feed input on the standard input, and expect output on the standard output as well.
```
cat compile_commands.json | ccdb-tool check > compatible_comile_commands.json
```


## Log Parser Heuristics
The clangify part is implemented with the heuristics for Clang compatibility defined in the CodeChecker library
log_parser. As long-term goal, the implementers of Compilation Datababase Transformer passes should be able to
reproduce these heuristics with the primitives defined in this library.

### BuildAction parsing
BuildAction is an Analyzer specific object, which is later
used by CodeChecker analyzers to drive the analysis process.

This parsing entails:
  * detecting the command part
    * first try `arguments` then `command` key in db
  * detecting the compiler
  * detect the BuildAction kind:
    * COMPILE, LINK, PREPROCESS, INFO



### Compiler detection
The compiler binary is is searched in the local
filesystem, and its `--version` invocation is
analyzed for:
  * compiler version number
  * detection of whether clang is used for ***both***
    compilation and analysis
  * presupposes the existence of binary
  * edge cases with ccache
      * ccache g++ main.cpp -> drop ccache
      * ccache main.cpp -> not handled
      * /usr/lib/ccache/gcc main.cpp -> use the symlink
  * offline parsing of compiler information could
    be useful


### Gcc2Clang

#### Replace
Add and remove operation
replace gcc/g++ build target options

```
-mips32     -> -target mips -mips32
-mips64     -> -target mips64 -mips64
-mpowerpc   -> -target powerpc
-mpowerpc64 -> -target powerpc64
```

#### Ignore specific compiler flags
For example, ignore any flags beginning with any of these regexes:
```
-Werror
-pedantic-errors
-w
```

#### Ignore if the original compiler is gcc
Ignore any flags beginning with any of these regexes,
(***only if  the original compiler is gcc!***)
Ignore flags unknown to clang.
Example:
```
-fno-jump-table
```

#### Ignore flags with parameters
These flags have parameters which also have to be ignored.
Example:
```
-install_name <param1>
-sectorder <param1> <param2> <param3>
```

### Extend entries with response files
If an command argument begins with `@` character
that signifies a response file. These files contain
gcc compatible command-line arguments. These are
returned, parameters are merged to the parameter list
of the original command, and positional arguments are added
to the source list of BuildAction being built.


### Skip specific BuildActions
Skip entries based on:
* Analysis skip handler configuration
* Whether or not ctu or statistics collection step is enabled

### BuildAction uniqueing
There can be multiple build-actions for a source file in
the compilation database. This can prove to be problematic
when doing lookup for a compiler invocation to produce AST.
Unique-ing is a way of circumventing this.

#### Uniqueing kinds
* alpha
  - if the source entries clash, use one which
    is not greater than any of the others lexicographically
* none
  - the hash of the entire command is used
* strict
  - emit error if there are multiple entries
    with the same source entry
* regex based custom
  - provided a regex, if source entries clash, use
    the single one matching the regex, but ***emit
    an error if multipe entries match***
