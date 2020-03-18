# Compilation Database Transformer

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
