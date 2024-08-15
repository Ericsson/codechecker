# Build Logger

This tool can capture the build process and generate a
[JSON Compilation Database](https://clang.llvm.org/docs/JSONCompilationDatabase.html)

## Compilation

To build the project execute
~~~~~~~
make all test
~~~~~~~

## Usage

Set the following environment variables:
~~~~~~~
export LD_PRELOAD=ldlogger.so
export LD_LIBRARY_PATH=`pwd`/build/lib:$LD_LIBRARY_PATH
export CC_LOGGER_GCC_LIKE="gcc:g++:clang:clang++:/cc:c++"
# The output compilation JSON file.
export CC_LOGGER_FILE=`pwd`/compilation.json
# Log linker build actions to the JSON file. Optional. Default: false
export CC_LOGGER_KEEP_LINK=true
~~~~~~~

then when you call `gcc` from a sub-shell (e.g. as a part of a Make build process),
 `compilation.json` will be created.
For example:
`bash -c "gcc -c something.c"`
will create
~~~~~~~
compilation.json:
[
	{
		"directory": "/home/john_doe/",
		"command": "/usr/bin/gcc-4.8 -c /home/john_doe/something.c",
		"file": "/home/john_doe/something.c"
	}
]
~~~~~~~



## Environment Variables

### `CC_LOGGER_GCC_LIKE`
You can change the compilers that should be logged.
Set `CC_LOGGER_GCC_LIKE` environment variable to a colon separated list.

For example (default):

```export CC_LOGGER_GCC_LIKE="gcc:g++:clang:clang++:/cc:c++"```

The logger will match any compilers with `gcc`,`g++`, `clang`, `clang++`, `cc`
and `c++` in their filenames.

This colon separated list may contain compiler names or paths. In case an
element of this list contains at least one slash (/) character then this is
considered a path. The logger will capture only those build actions which have
this postfix:

```sh
export CC_LOGGER_GCC_LIKE="gcc:/bin/g++:clang:clang++:/cc:c++"

# "gcc" has to be infix of the compiler's name because it contains no slash.
# "/bin/g++" has to be postfix of the compiler's path because it contains slash.

my/gcc/compiler/g++ main.cpp  # Not captured because there is no match.
my/gcc/compiler/gcc-7 main.c  # Captured because "gcc" is infix of "gcc-7".
/usr/bin/g++ main.cpp         # Captured because "/bin/g++" is postfix of the compiler path.
/usr/bin/g++-7 main.cpp       # Not captured because "/bin/g++" is not postfix of the compiler path.

# For an exact compiler binary name match start the binary name with a "/".
/clang # Will not log clang++ calls only the clang binary calls will be captured.
clang  # Will capture clang-tidy (which is not wanted) calls too because of a partial match.
```

The reason of having a slash before `cc` is that `cc1` binary is executed as
a sub-process by some compilers and that shouldn't be captured.

### `CC_LOGGER_FILE`
Output file to generate compilation database into.
This can be a relative or absolute path.

### `CC_LOGGER_JAVAC_LIKE`
You can specify the `javac` like
compilers that should be logged as a colon separated string list.

### `CC_LOGGER_DEF_DIRS`
If the environment variable is defined, the logger will extend the compiler
argument list in the compilation database with the pre-configured include paths
of the logged compiler.

### `CC_LOGGER_ABS_PATH`
If the environment variable is defined,
all relative paths in the compilation commands after
`-I, -idirafter, -imultilib, -iquote, -isysroot -isystem,
-iwithprefix, -iwithprefixbefore, -sysroot, --sysroot`
will be converted to absolute PATH when written into the compilation database.

### `CC_LOGGER_DEBUG_FILE`
Output file to print log messages. If this environment variable is not
defined it will do nothing.

### `CC_LOGGER_KEEP_LINK`
This environment variable is optional. If its value is not `true` then object
files will be removed from the build action. For example in case of this build
command: `gcc main.c object1.o object2.so` the `object1.o` and `object2.so`
will be removed and only `gcc main.c` will be captured. If only object files
are provided to the compiler then the complete build action will be thrown
away. This means that build actions which only perform linking will not be
captured. We consider a file as object file if its extension is `.o`, `.so` or
`.a`.
