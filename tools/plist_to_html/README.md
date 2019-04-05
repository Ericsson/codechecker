# plist-to-html
`plist-to-html` is a python tool which parses and creates HTML files from one
or more `.plist` result files.

## Install guide
```sh
# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install plist-to-html package.
make package
```

## Usage
```sh
usage: plist-to-html [-h] -o OUTPUT_DIR [-l LAYOUT_DIR]
                     file/folder [file/folder ...]

Parse and create HTML files from one or more '.plist' result files.

positional arguments:
  file/folder           The plist files and/or folders containing analysis
                        results which should be parsed.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output OUTPUT_DIR
                        Generate HTML output files in the given folder.
                        (default: None)
  -l LAYOUT_DIR, --layout LAYOUT_DIR
                        Directory which contains dependency HTML, CSS and
                        JavaScript files. (default: plist_to_html/../static)
```

## License

The project is licensed under University of Illinois/NCSA Open Source License.
See LICENSE.TXT for details.