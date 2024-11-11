# tu-collector
`tu-collector` is a python tool which collects the source files constituting a
translation unit. This script does this action based on a compilation database
JSON file. The output of the script is a ZIP package with the collected
sources.

## Install guide
```sh
# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install tu-collector package.
make package
```

## Usage
<details>
  <summary>
    <i>$ <b>tu_collector --help</b> (click to expand)</i>
  </summary>

```
usage: tu_collector [-h] (-b COMMAND | -l LOGFILE) [-f FILTER] (-z ZIP | -d)
                    [-v]

This script can be used for multiple purposes:
- It can be used to collect all the source files constituting specific
translation units. The files are written to a ZIP file which will contain the
sources preserving the original directory hierarchy.
- It can be used to get source files which depend on a given header file.

optional arguments:
  -h, --help            show this help message and exit
  -f FILTER, --filter FILTER
                        If '--zip' option is given this flag restricts the
                        collection on the build actions of which the compiled
                        source file matches this path. If '--dependents'
                        option is given this flag specify a header file to get
                        source file dependencies for. E.g.: /path/to/*/files
  -v, --verbose         Enable debug level logging.

log arguments:

  Specify how the build information database should be obtained. You need to
  specify either an already existing log file, or a build command which will be
  used to generate a log file on the fly.

  -b COMMAND, --build COMMAND
                        Execute and record a build command. Build commands can
                        be simple calls to 'g++' or 'clang++'.
  -l LOGFILE, --logfile LOGFILE
                        Use an already existing JSON compilation command
                        database file specified at this path.

output arguments:
  Specify the output type.

  -z ZIP, --zip ZIP     Output ZIP file.
  -d, --dependents      Use this flag to return a list of source files which
                        depend on some header files specified by the --filter
                        option. The result will not contain header files, even
                        if those are dependents as well.
```
</details>

## Get source files which include a specific header file
Header files can not be analyzed without a C/C++ file. If you change a header
file this tool can be used to find all the C/C++ source files including that
header file. You can create a skip file and include only these source files
so the header file will be actually "analyzed".

**WARNING**: full compilation database is required to collect this information.

### Get source file dependencies for a header
You can use this tool to get all source file dependencies for a given header
file:

```sh
# Using absolute path.
tu_collector --dependents -l ./full_compilation_database.json -f "/path/to/main.h"

# Using relative path.
tu_collector --dependents -l ./full_compilation_database.json -f "*/main.h"
```

### Create skip file from source files that need to be reanalyzed
You can use this tool to get all source file dependencies for all the changed
header files in a git commit and create a skip file from all source files that
need to be reanalyzed by the `CodeChecker analyze` command:

```sh
#!/bin/bash

# Full compilation database file.
compilation_database="./full_compilation_database.json"

# Skip file for CodeChecker analyze command.
skip_file="./skipfile"

# Remove skip file if exists.
rm -rf $skip_file

# Use git to get changed header files, use tu_collector to get all source files
# that need to be reanalyzed and include them in the skip file.
changed_header_files=$(git diff --name-only HEAD^ -- '*.h' '*.hpp')
for changed_header in $changed_header_files; do
  source_files=$(tu_collector --dependents -l "$compilation_database" -f "*$changed_header")
  for source_file in $source_files; do
    echo "+$(pwd)/$source_file" >> $skip_file;
  done
done

# Use git to get changed source files and include them in the skip file.
changed_source_files=$(git diff --name-only HEAD^ -- '*.c' '*.cpp')
for source_file in $changed_source_files; do
  echo "+$(pwd)/$source_file" >> $skip_file;
done

# Exclude every other files from the analysis.
echo "-*" >> $skip_file
```

## License

The project is licensed under Apache License v2.0 with LLVM Exceptions.
See LICENSE.TXT for details.