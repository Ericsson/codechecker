# report-converter
`report-converter` is a Python tool which can be used to create a CodeChecker
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
  * [Leak Sanitizer](#leak-sanitizer)
* [Cppcheck](#cppcheck)
* [Spotbugs](#spotbugs)
* [Facebook Infer](#facebook-infer)
* [ESLint](#eslint)
* [Pylint](#pylint)
* [TSLint](#tslint)
* [Golint](#golint)
* [Pyflakes](#pyflakes)
* [Markdownlint](#markdownlint)
* [Coccinelle](#coccinelle)
* [Smatch](#smatch)
* [Kernel-Doc](#kernel-doc)
* [Sphinx](#sphinx)
* [Sparse](#sparse)
* [cpplint](#cpplint)
* [License](#license)

## Install guide
```sh
# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install report-converter package.
make package
```

## Usage
<details>
  <summary><i>$ <b>report-converter --help</b> (click to expand)</i></summary>

```
usage: report-converter [-h] -o OUTPUT_DIR -t TYPE [--meta [META [META ...]]]
                        [--filename FILENAME] [-c] [-v]
                        file

Creates a CodeChecker report directory from the given code analyzer output
which can be stored to a CodeChecker web server.

positional arguments:
  file                  Code analyzer output result file which will be parsed
                        and used to generate a CodeChecker report directory.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output OUTPUT_DIR
                        This directory will be used to generate CodeChecker
                        report directory files.
  -t TYPE, --type TYPE  Specify the format of the code analyzer output.
                        Currently supported output types are: asan, clang-
                        tidy, coccinelle, cppcheck, cpplint, eslint,
                        fbinfer, golint, kernel-doc, lsan, mdl, msan, 
                        pyflakes, pylint, smatch, sparse, sphinx, spotbugs, 
                        tsan, tslint, ubsan.
  --meta [META [META ...]]
                        Metadata information which will be stored alongside
                        the run when the created report directory will be
                        stored to a running CodeChecker server. It has the
                        following format: key=value. Valid key values are:
                        analyzer_command, analyzer_version. (default: None)
  --filename FILENAME   This option can be used to override the default plist
                        file name output of this tool. This tool can produce
                        multiple plist files on the given code analyzer output
                        result file. The problem is if we run this tool
                        multiple times on the same directory, it may override
                        some plist files. To prevent this we can generate a
                        unique hash into the plist file names with this
                        option. For example: '{source_file}_{analyzer}_xxxxx'.
                        {source_file} and {analyzer} are special values which
                        will be replaced with the current analyzer and source
                        file name where the bug was found. (default:
                        {source_file}_{analyzer})
  -c, --clean           Delete files stored in the output directory. (default:
                        False)
  -v, --verbose         Set verbosity level. (default: False)

Supported analyzers:
  asan - AddressSanitizer, https://clang.llvm.org/docs/AddressSanitizer.html
  clang-tidy - Clang Tidy, https://clang.llvm.org/extra/clang-tidy
  coccinelle - Coccinelle, https://github.com/coccinelle/coccinelle
  cppcheck - Cppcheck, http://cppcheck.sourceforge.net
  cpplint - cpplint, https://github.com/cpplint/cpplint
  eslint - ESLint, https://eslint.org/
  fbinfer - Facebook Infer, https://fbinfer.com
  golint - Golint, https://github.com/golang/lint
  kernel-doc - Kernel-Doc, https://github.com/torvalds/linux/blob/master/scripts/kernel-doc
  lsan - LeakSanitizer, https://clang.llvm.org/docs/LeakSanitizer.html
  mdl - Markdownlint, https://github.com/markdownlint/markdownlint
  msan - MemorySanitizer, https://clang.llvm.org/docs/MemorySanitizer.html
  pyflakes - Pyflakes, https://github.com/PyCQA/pyflakes
  pylint - Pylint, https://www.pylint.org
  smatch - Smatch, https://repo.or.cz/w/smatch.git
  sparse - Sparse, https://git.kernel.org/pub/scm/devel/sparse/sparse.git
  sphinx - Sphinx, https://github.com/sphinx-doc/sphinx
  spotbugs - spotbugs, https://spotbugs.github.io
  tsan - ThreadSanitizer, https://clang.llvm.org/docs/ThreadSanitizer.html
  tslint - TSLint, https://palantir.github.io/tslint
  ubsan - UndefinedBehaviorSanitizer, https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
```
</details>

## Sanitizers
### [Undefined Behaviour Sanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)
- Compile with `-g` and `-fno-omit-frame-pointer` to get proper debug
  information in your binary.
- Run your program with environment variable
  `UBSAN_OPTIONS=print_stacktrace=1`.
- Set the `UBSAN_SYMBOLIZER_PATH` environment variable to point to the
  `llvm-symbolizer` binary (or make sure `llvm-symbolizer` is in your `$PATH`).
- Run the `report-converter` converter from the directory where your binary
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
report-converter -t ubsan -o ./ubsan_results ubsan.output
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
report-converter -t asan -o ./asan_results asan.output
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
report-converter -t msan -o ./msan_results msan.output
```

### [Thread Sanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html)
- Compile with `-g` to get proper debug information in your binary.

```sh
# Compile your program.
clang++ -fsanitize=thread -g tsan.cpp

# Run your program and redirect the output to a file.
./a.out > tsan.output 2>&1

# Generate plist files from the output.
report-converter -t tsan -o ./tsan_results tsan.output
```

### [Leak Sanitizer](https://clang.llvm.org/docs/LeakSanitizer.html)
- Compile with `-g` and `-fsanitize=address`  to get proper debug information in your binary.
```sh
# Compile your program.
clang -fsanitize=address -g lsan.c

# Run your program and redirect the output to a file.
ASAN_OPTIONS=detect_leaks=1 ./a.out > lsan.output 2>&1

# Generate plist files from the output.
report-converter -t lsan -o ./lsan_results lsan.output
```

## [Cppcheck](http://cppcheck.sourceforge.net/)
[Cppcheck](http://cppcheck.sourceforge.net/) is a static analysis tool for
`C/C++` code.

The recommended way of running the Cppcheck tool is to use a
[JSON Compilation Database](https://clang.llvm.org/docs/JSONCompilationDatabase.html)
file.

The following example shows how to log the compilation commands with
CodeChecker, run CppCheck and store the results found by CppCheck to the
CodeChecker database.

```sh
# Collect the compilation commands with absolute path conversion.
# Absolute path conversion is required so the reports generated by Cppcheck can
# be stored.
CC_LOGGER_ABS_PATH=1 CodeChecker log -o compile_command.json -b "make"

# Create a directory for the reports.
mkdir cppcheck_reports

# Run Cppcheck by using the generated compile command database.
cppcheck --project=compile_command.json --plist-output=./cppcheck_reports

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Cppcheck. It will generate a unique report identifier
report-converter -t cppcheck -o ./codechecker_cppcheck_reports ./cppcheck_reports

# Store the Cppcheck reports with CodeChecker.
CodeChecker store ./codechecker_cppcheck_reports -n cppcheck
```

*Notes*:
- The missing unique report identifiers will be generated by the
`report-converter` tool.
- Analysis related information can not be stored since it is not collected by
CppCheck: `analysis statistics`, `analysis duration`, `cppcheck command` etc.

For more information about logging checkout the log section in the
[user guide](/docs/usage.md).

## [Spotbugs](https://spotbugs.github.io/)
[Spotbugs](https://spotbugs.github.io/) is a static analysis tool for `Java`
code.

The recommended way of running the Spotbugs tool is to generate an xml output
file with messages (`-xml:withMessages`).

The following example shows you how to run SpotBugs and store the results
found by SpotBugs to the CodeChecker database.

```sh
# Run SpotBugs.
# Use the '-xml:withMessages' option to generate xml output.
spotbugs -xml:withMessages -output ./bugs.xml -textui /path/to/your/project

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of SpotBugs.
report-converter -t spotbugs -o ./codechecker_spotbugs_reports ./bugs.xml

# Store the SpotBugs reports with CodeChecker.
CodeChecker store ./codechecker_spotbugs_reports -n spotbugs
```

## [Facebook Infer](https://fbinfer.com/)
[Facebook Infer](https://fbinfer.com/) is a static analysis tool developed by
Facebook which supports multiple programming languages such as `C/C++`, `Java`
etc.

The recommended way of running the Facebook Infer tool is to generate an
`infer-out` directory which will contain a `report.json` file.

The following example shows you how to run Facebook Infer and store the results
found by Infer to the CodeChecker database.

```sh
# Run Infer.
infer capture -- clang++ main.cpp
infer analyze

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of FB Infer.
report-converter -t fbinfer -o ./codechecker_fbinfer_reports ./infer-out

# Store the Infer reports with CodeChecker.
CodeChecker store ./codechecker_fbinfer_reports -n fbinfer
```

## [ESLint](https://eslint.org)
[ESLint](https://eslint.org) is a static analysis tool for `JavaScript`.

The recommended way of running the ESLint tool is to generate a json output
file.

The following example shows you how to run ESLint and store the results found
by ESLint to the CodeChecker database.

```sh
# Run ESLint.
eslint -o ./eslint_reports.json -f json /path/to/my/project

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of ESLint.
report-converter -t eslint -o ./codechecker_eslint_reports ./eslint_reports.json

# Store the ESLint reports with CodeChecker.
CodeChecker store ./codechecker_eslint_reports -n eslint
```

## [Pylint](https://www.pylint.org)
[Pylint](https://www.pylint.org) is a static analysis tool for `Python`.

The recommended way of running the Pylint tool is to generate a `json` output
file.

The following example shows you how to run Pylint and store the results found
by Pylint to the CodeChecker database.

```sh
# Run Pylint.
pylint -f json /path/to/my/project > ./pylint_reports.json

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Pylint.
report-converter -t pylint -o ./codechecker_pylint_reports ./pylint_reports.json

# Store the Pylint reports with CodeChecker.
CodeChecker store ./codechecker_pylint_reports -n pylint
```

## [Pyflakes](https://github.com/PyCQA/pyflakes)
[Pyflakes](https://github.com/PyCQA/pyflakes) is a static analysis tool for
`Python` code.

The recommended way of running Pyflakes is to redirect the output to a file and
give this file to the report converter tool.

The following example shows you how to run Pyflakes and store the results
found by Pyflakes to the CodeChecker database.

```sh
# Run Pyflakes.
pyflakes /path/to/your/project > ./pyflakes_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Pyflakes.
report-converter -t pyflakes -o ./codechecker_pyflakes_reports ./pyflakes_reports.out

# Store the Pyflakes reports with CodeChecker.
CodeChecker store ./codechecker_pyflakes_reports -n pyflakes
```

## [TSLint](https://palantir.github.io/tslint)
[TSLint](https://palantir.github.io/tslint) is a static analysis tool for
`TypeScript`.

The recommended way of running the TSLint tool is to generate a **json** output
file.

The following example shows you how to run TSLint and store the results found
by TSLint to the CodeChecker database.

```sh
# Run TSLint.
tslint --format json /path/to/my/ts/file -o ./tslint_reports.json

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of TSLint.
report-converter -t tslint -o ./codechecker_tslint_reports ./tslint_reports.json

# Store the TSLint reports with CodeChecker.
CodeChecker store ./codechecker_tslint_reports -n tslint
```

## [Golint](https://github.com/golang/lint)
[Golint](https://github.com/golang/lint) is a static analysis tool for `Go`
code.

The recommended way of running Golint is to redirect the output to a file and
give this file to the report converter tool.

The following example shows you how to run Golint and store the results
found by Golint to the CodeChecker database.

```sh
# Run Golint.
golint /path/to/your/project > ./golint_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Golint.
report-converter -t golint -o ./codechecker_golint_reports ./golint_reports.out

# Store the Golint reports with CodeChecker.
CodeChecker store ./codechecker_golint_reports -n golint
```

## [Markdownlint](https://github.com/markdownlint/markdownlint)
[Markdownlint](https://github.com/markdownlint/markdownlint) is a static
analysis tool for markdown files.

The recommended way of running Markdownlint is to redirect the output to a file
and give this file to the report converter tool.

The following example shows you how to run Markdownlint and store the results
found by Markdownlint to the CodeChecker database.

```sh
# Run Markdownlint.
mdl /path/to/your/project > ./mdl_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Markdownlint.
report-converter -t mdl -o ./codechecker_mdl_reports ./mdl_reports.out

# Store Markdownlint reports with CodeChecker.
CodeChecker store ./codechecker_mdl_reports -n mdl
```

## [Coccinelle](https://github.com/coccinelle/coccinelle)
[Coccinelle](https://github.com/coccinelle/coccinelle) allows programmers to easily 
write some complex style-preserving source-to-source transformations on C source code, 
like for instance to perform some refactorings.

The recommended way of running Coccinelle is to redirect the output to a file and
give this file to the report converter tool.

Note: the checker name will be the file name of the `.cocci` file along with `cocinelle` prefix.

The following example shows you how to run Coccinelle on kernel sources 
and store the results found by Coccinelle to the CodeChecker database.
```sh
# Change Directory to your project
cd path/to/linux/kernel/repository

# Run Coccicheck 
make coccicheck MODE=report V=1 > ./coccinelle_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Coccicheck
report-converter -t coccinelle -o ./codechecker_coccinelle_reports ./coccinelle_reports.out

# Store the Cocccinelle reports with CodeChecker.
CodeChecker store ./codechecker_coccinelle_reports -n coccinelle
```

## [Smatch](https://repo.or.cz/w/smatch.git)
[Smatch](https://repo.or.cz/w/smatch.git) is a static analysis tool for C that is used on the kernel.

The recommended way of running Smatch is to redirect the output to a file and
give this file to the report converter tool.

The following example shows you how to run Smatch on kernel sources 
and store the results found by Smatch to the CodeChecker database.
```sh
# Change Directory to your project
cd path/to/linux/kernel/repository

# Run Smatch 
# Note: The warnings will be stored by default into smatch_warns.txt after executing the following command
path/to/smatch/smatch_scripts/test_kernel.sh

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Smatch
report-converter -t smatch -o ./codechecker_smatch_reports ./smatch_warns.txt

# Store the Smatch reports with CodeChecker.
CodeChecker store ./codechecker_smatch_reports -n smatch
```

## [Kernel-Doc](https://github.com/torvalds/linux/blob/master/scripts/kernel-doc)
[Kernel-Doc](https://github.com/torvalds/linux/blob/master/scripts/kernel-doc) structure is extracted 
from the comments, and proper Sphinx C Domain function and type descriptions with anchors are generated 
from them. The descriptions are filtered for special kernel-doc highlights and cross-references.

The recommended way of running Kernel-Doc is to redirect the output to a file and
give this file to the report converter tool.

The following example shows you how to run Kernel-Doc on kernel sources 
and store the results found by Kernel-Doc to the CodeChecker database.
```sh
# Change Directory to your project
cd path/to/linux/kernel/repository

# Run Kernel-Doc
# Note: The output of the following command will be both of sphinx and kernel-doc, 
# but the parser will parse only kernel-doc output
make htmldocs 2>&1 | tee kernel-docs.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Kernel-Doc
report-converter -t kernel-doc -o ./codechecker_kernel_doc_reports ./kernel-docs.out

# Store the Kernel-Doc reports with CodeChecker.
CodeChecker store ./codechecker_kernel_doc_reports -n kernel-doc
```

## [Sphinx](https://github.com/sphinx-doc/sphinx)
[Sphinx](https://github.com/sphinx-doc/sphinx) Sphinx is a documentation generator 
or a tool that translates a set of plain text source files into various output formats, 
automatically producing cross-references, indices, etc.

The recommended way of running Sphinx is to redirect the output to a file and
give this file to the report converter tool.

The following example shows you how to run Sphinx on kernel sources 
and store the results found by Sphinx to the CodeChecker database.

```sh
# Change Directory to your project
cd path/to/linux/kernel/repository

# Run Sphinx
# Note: The output of the following command will be both of sphinx and kernel-doc, 
# but the parser will parse only sphinx output
make htmldocs 2>&1 | tee sphinx.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Sphinx
report-converter -t sphinx -o ./codechecker_sphinx_reports ./sphinx.out

# Store the Sphinx reports with CodeChecker.
CodeChecker store ./codechecker_sphinx_reports -n sphinx
```

## [Sparse](https://git.kernel.org/pub/scm/devel/sparse/sparse.git)
[Sparse](https://git.kernel.org/pub/scm/devel/sparse/sparse.git) is a semantic checker 
for C programs; it can be used to find a number of potential problems with kernel code.

The recommended way of running Sparse is to redirect the output to a file and
give this file to the report converter tool.

The following example shows you how to run Sparse on kernel sources 
and store the results found by Sparse to the CodeChecker database.

```sh
# Change Directory to your project
cd path/to/linux/kernel/repository

# Run Sparse
make C=1 2>&1 | tee sparse.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Sparse
report-converter -t sparse -o ./codechecker_sparse_reports ./sparse.out

# Store the Sparse reports with CodeChecker.
CodeChecker store ./codechecker_sparse_reports -n sparse
```

## [cpplint](https://github.com/cpplint/cpplint)
[cpplint](https://github.com/cpplint/cpplint) is a lint-like tool which checks
C++ code against [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html).

The recommended way of running cpplint is to redirect the output to a file and
give this file to the report converter tool.

The following example shows you how to run cpplint and store the results
found by cpplint to the CodeChecker database.

```sh
# Change Directory to your project
cd path/to/your/project

# Run cpplint
cpplint sample.cpp > ./sample.out 2>&1

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of cpplint
report-converter -t cpplint -o ./codechecker_cpplint_reports ./sample.out

# Store the cpplint reports with CodeChecker.
CodeChecker store ./codechecker_cpplint_reports -n cpplint
```

## License

The project is licensed under Apache License v2.0 with LLVM Exceptions.
See LICENSE.TXT for details.
