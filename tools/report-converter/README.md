# CodeChecker Report Converter

A Python tool to parse and convert various code analyzer outputs into CodeChecker format. It can create HTML reports from analyzer outputs and store them in a CodeChecker server.

## Quick Start

```bash
# Create a Python virtualenv and set it as your environment
make venv
source $PWD/venv/bin/activate

# Build and install report-converter package
make package
```

## Basic Usage

```bash
# Convert analyzer output to CodeChecker format
report-converter --type clang-tidy --output /path/to/reports clang-tidy-output.txt

# Generate HTML report
plist-to-html --input /path/to/reports/*.plist --output /path/to/html
```

## Documentation

For comprehensive documentation, including:
- Complete list of supported analyzers
- Detailed usage examples
- Configuration options
- Troubleshooting guide

Please visit our [official documentation](https://codechecker.readthedocs.io/en/latest/tools/report-converter/).

## Requirements

- Python >= 3.8

## License

This project is licensed under the Apache License 2.0 - see the LICENSE.txt file for details.

## Authors

CodeChecker Team (Ericsson)
