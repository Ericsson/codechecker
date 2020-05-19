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
```sh
usage: tu_collector.py [-h] (-b COMMAND | -l LOGFILE) -z ZIP [-f FILTER]

This script collects all the source files constituting specific translation
units. The files are written to a ZIP file which will contain the sources
preserving the original directory hierarchy.

optional arguments:
  -h, --help            show this help message and exit
  -z ZIP, --zip ZIP     Output ZIP file.
  -f FILTER, --filter FILTER
                        This flag restricts the collection on the build
                        actions of which the compiled source file matches this
                        path. E.g.: /path/to/*/files

log arguments:
  Specify how the build information database should be obtained. You need to
  specify either an already existing log file, or a build command which will
  be used to generate a log file on the fly.

  -b COMMAND, --build COMMAND
                        Execute and record a build command. Build commands can
                        be simple calls to 'g++' or 'clang++'.
  -l LOGFILE, --logfile LOGFILE
                        Use an already existing JSON compilation command
                        database file specified at this path.
```

## License

The project is licensed under Apache License v2.0 with LLVM Exceptions.
See LICENSE.TXT for details.