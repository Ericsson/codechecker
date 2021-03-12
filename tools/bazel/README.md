# Bazel compilation database generator
`bazel-compile-commands` is a python tool which generates compilation database
(`compile_commands.json` file) from Bazel build command.

The tool uses `bazel aquery` command output to produce compile commands
without executing build itself.

## Install guide
```sh
# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install bazel-compile-commands package.
make package
```

## Usage
<details>
  <summary>
    <i>$ <b>bazel-compile-commands --help</b> (click to expand)</i>
  </summary>

```
usage: bazel-compile-commands [-h] [-o OUTPUT] [-b BUILD] [-v]

Run bazel aquery to produce compilation database (compile_commands.json)
for particular bazel build command

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        output compile_commands.json file
  -b BUILD, --build BUILD
                        bazel build command arguments
  -v, --verbosity       increase output verbosity (e.g., -v or -vv)
```
</details>

## License

The project is licensed under Apache License v2.0 with LLVM Exceptions.
See LICENSE.TXT for details.
