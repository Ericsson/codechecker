# warning-to-plist
`warning-to-plist` is a Python tool which can be used to create a CodeChecker
report directory from the given code analyzer output which can be stored to
a CodeChecker server.

## Table of Contents
* [Install guide](#install-guide)
* [Usage](#usage)
* [Sanitizers](#sanitizers)
  * [Undefined Behaviour Sanitizer](#undefined-behaviour-sanitizer)
  * [Address Sanitizer](#address-sanitizer)
  * [Memory Sanitizer](#memory-sanitizer)
  * [Thread Sanitizer](#thread-sanitizer)
* [License](#license)

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
                        Currently supported output types are: asan, tsan,
                        ubsan, msan, clang-tidy.
  -c, --clean           Delete files stored in the output directory.
  -v, --verbose         Set verbosity level. (default: False)
```

## Sanitizers
### [Undefined Behaviour Sanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)
- Compile with `-g` and `-fno-omit-frame-pointer` to get proper debug
  information in your binary.
- Run your program with environment variable
  `UBSAN_OPTIONS=print_stacktrace=1`.
- Set the `UBSAN_SYMBOLIZER_PATH` environment variable to point to the
  `llvm-symbolizer` binary (or make sure `llvm-symbolizer` is in your `$PATH`).
- Run the `warning-to-plist` converter from the directory where your binary
  is because the output of the `UndefinedBehaviorSanitizer` will contain
  relative paths.

```sh
# Compile your program.
clang++ -fsanitize=undefined -g -fno-omit-frame-pointer ubsanitizer.cpp

# Run your program and redirect the output to a file.
UBSAN_OPTIONS=print_stacktrace=1 \
UBSAN_SYMBOLIZER_PATH=/usr/lib/llvm-6.0/bin/llvm-symbolizer \
./a.out > ubsan.output 2>&1

# Generate plist files from the output.
warning-to-plist -t ubsan -o ./ubsan_results ubsan.output
```

### [Address Sanitizer](https://clang.llvm.org/docs/AddressSanitizer.html)
- Compile with `-g` and `-fno-omit-frame-pointer` to get proper debug
  information in your binary.
- Set the `ASAN_SYMBOLIZER_PATH` environment variable to point to the
  `llvm-symbolizer` binary (or make sure `llvm-symbolizer` is in your `$PATH`).

```sh
# Compile your program.
clang++ -fsanitize=address -g -fno-omit-frame-pointer asan.cpp

# Run your program and redirect the output to a file.
ASAN_SYMBOLIZER_PATH=/usr/lib/llvm-6.0/bin/llvm-symbolizer \
./a.out > asan.output 2>&1

# Generate plist files from the output.
warning-to-plist -t asan -o ./asan_results asan.output
```

### [Memory Sanitizer](https://clang.llvm.org/docs/MemorySanitizer.html)
- Compile with `-g` and `-fno-omit-frame-pointer` to get proper debug
  information in your binary.
- Set the `MSAN_SYMBOLIZER_PATH` environment variable to point to the
  `llvm-symbolizer` binary (or make sure `llvm-symbolizer` is in your `$PATH`).

```sh
# Compile your program.
clang++ -fsanitize=memory -g -fno-omit-frame-pointer msan.cpp

# Run your program and redirect the output to a file.
MSAN_SYMBOLIZER_PATH=/usr/lib/llvm-6.0/bin/llvm-symbolizer \
./a.out > msan.output 2>&1

# Generate plist files from the output.
warning-to-plist -t msan -o ./msan_results msan.output
```

### [Thread Sanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html)
- Compile with `-g` to get proper debug information in your binary.

```sh
# Compile your program.
clang++ -fsanitize=thread -g tsan.cpp

# Run your program and redirect the output to a file.
./a.out > tsan.output 2>&1

# Generate plist files from the output.
warning-to-plist -t tsan -o ./tsan_results tsan.output
```

## License

The project is licensed under University of Illinois/NCSA Open Source License.
See LICENSE.TXT for details.