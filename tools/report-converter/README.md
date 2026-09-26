# CodeChecker Report Converter

A Python tool to parse and convert various code analyzer outputs into CodeChecker format. It can create HTML reports from analyzer outputs and store them in a CodeChecker server.

## Quick Start

`report-converter` is part of the CodeChecker package, it is not distributed as
a standalone package. It is installed together with CodeChecker:

```bash
pip3 install codechecker
```

To use it from the source, build a CodeChecker package in the **root** of the
repository:

```bash
# Create a Python virtualenv and set it as your environment
make venv
source $PWD/venv/bin/activate

# Build a CodeChecker package
make package

# For ease of access, add the build directory to PATH. It contains the
# 'report-converter' entry point of the built package.
export PATH="$PWD/build/CodeChecker/bin:$PATH"
```

## Basic Usage

```bash
# Convert analyzer output to CodeChecker format
report-converter --type clang-tidy --output /path/to/reports clang-tidy-output.txt

# Generate HTML report from the converted reports
CodeChecker parse --export html --output /path/to/html /path/to/reports
```

## Documentation

For comprehensive documentation, including:
- Complete list of supported analyzers
- Detailed usage examples
- Configuration options
- Troubleshooting guide

Please visit our [official documentation](https://codechecker.readthedocs.io/en/latest/tools/report-converter/).

## Requirements

- Python >= 3.11

## License

This project is licensed under the Apache License 2.0 - see the LICENSE.txt file for details.

## Authors

CodeChecker Team (Ericsson)