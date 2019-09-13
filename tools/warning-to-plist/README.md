# warning-to-plist
`warning-to-plist` is a Python tool which can be used to create a CodeChecker
report directory from the given code analyzer output which can be stored to
a CodeChecker server.

## Install guide
```sh
# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install warning-to-plist package.
make package
```

## Usage
```sh
usage: warn-to-plist [-h] -o OUTPUT_DIR -t TYPE [-c] [-v] [file]

Creates a CodeChecker report directory from the given code analyzer output
which can be stored to a CodeChecker web server.

positional arguments:
  file                  Code analyzer output result file which will be parsed
                        and used to generate a CodeChecker report directory.
                        If this parameter is not given the standard input will
                        be used.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output OUTPUT_DIR
                        This directory will be used to generate CodeChecker
                        report directory files.
  -t TYPE, --type TYPE  Specify the format of the code analyzer output.
                        Currently supported output types are: clang-tidy.
  -c, --clean           Delete files stored in the output directory.
  -v, --verbose         Set verbosity level. (default: False)
```

## License

The project is licensed under University of Illinois/NCSA Open Source License.
See LICENSE.TXT for details.