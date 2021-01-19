# merge-clang-extdef-mappings
As the collect phase runs parallel on multiple threads, all compilation units
are separately mapped into a temporary file in a temporary folder. These
function maps contain the mangled names of functions and the source (AST
generated from the source) which had them. These files should be merged at
the end into a global map file.

`merge-clang-extdef-mappings` is a python tool which can be used to merge
individual function maps created by the
[clang-extdef-mapping](https://github.com/llvm/llvm-project/blob/master/clang/tools/clang-extdef-mapping/ClangExtDefMapGen.cpp)
tool into a global one.


## Install guide
```sh
# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install plist-to-html package.
make package
```

## Usage
<details>
  <summary>
    <i>$ <b>merge-clang-extdef-mappings --help</b> (click to expand)</i>
  </summary>

```
usage: merge-clang-extdef-mappings [-h] -i input -o output

Merge individual clang extdef mapping files into one mapping file.

optional arguments:
  -h, --help            show this help message and exit
  -i input, --input input
                        Folder which contains multiple output of the 'clang-
                        extdef-mapping' tool.
  -o output, --output output
                        Output file where the merged function maps will be
                        stored into.

Example:
  merge-clang-extdef-mappings -i /path/to/fn_map_folder -o
  /path/to/externalDefMap.txt
```
</details>

## License

The project is licensed under University of Illinois/NCSA Open Source License.
See LICENSE.TXT for details.