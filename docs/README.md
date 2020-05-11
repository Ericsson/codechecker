<h1 align="center">
  <br>
  <img src="https://github.com/Ericsson/codechecker/raw/master/docs/logo/logo_blue.png" alt="CodeChecker" width="200">
  <br>
  CodeChecker
  <br>
</h1>

<p align="center">
  <a href="https://travis-ci.org/Ericsson/codechecker">
    <img src="https://travis-ci.org/Ericsson/codechecker.png?branch=master"
         alt="Travis">
  </a>
  <a href="https://gitter.im/codecheckerHQ/Lobby?utm_source=share-link&utm_medium=link&utm_campaign=share-link">
    <img src="https://badges.gitter.im/codecheckerHQ/Lobby.svg"
         alt="Gitter">
  </a>
  <a href="https://codechecker.readthedocs.io/en/latest/?badge=latest">
    <img src="https://readthedocs.org/projects/codechecker/badge/?version=latest"
         alt="Documentation Status">
  </a>
</p>

**CodeChecker** is a static analysis infrastructure built on the [LLVM/Clang
Static Analyzer](http://clang-analyzer.llvm.org) toolchain, replacing
[`scan-build`](http://clang-analyzer.llvm.org/scan-build.html) in a Linux or
macOS (OS X) development environment.

**CodeChecker is ported to Python3!**  
**No Python2 support is planned. The minimal required Python3 version is 3.6.**  
**Old virtual environments needs to be removed!**

![Web interface showing list of analysed projects and bugs](images/demo.gif)


# Main features

  * Support for multiple analyzers, currently
    [_Clang Static Analyzer_](http://clang-analyzer.llvm.org/) and
    [_Clang-Tidy_](http://clang.llvm.org/extra/clang-tidy/)
  * Store results of multiple large-scale analysis runs efficiently, either in
    a PostgreSQL or SQLite database
  * **Web application** for viewing discovered code defects with a streamlined,
    easy experience
  * **Filterable** (defect checker name, severity, source paths, ...) and
    **comparable** (calculates difference between two analyses of the project,
    showing which bugs have been fixed and which are newly introduced) result
    viewing
  * Subsequent analysis runs **only check** and update results for **modified
    files** without analysing the _entire_ project (depends on build toolchain
    support!)
  * See the list of bugs that has been introduced since your last analyzer
    execution
  * Suppression of known false positive results, either in configuration file
    or via annotation in source code, along with exclusion of entire source
    paths from analysis
  * Results can be shared with fellow developers, the **comments** and
    **review** system helps communication of code defects
  * Can show analysis results on standard output
  * Easily implementable [Thrift](http://thrift.apache.org)-based
    server-client communication used for storing and querying of discovered
    defects
  * Support for multiple bug visualisation frontends, such as the web
    application, a [command-line tool](usage.md) and an
    [Eclipse plugin](http://github.com/Ericsson/CodeCheckerEclipsePlugin)


# User documentation

* [Getting started (How-To with examples)](usage.md)
* [Analyzer User guide](analyzer/user_guide.md)
* [Webserver User guide](web/user_guide.md)
* [Requiring credentials to view analysis results](web/authentication.md)
* [Overview about connecting multiple analysis run databases](web/products.md)
* [Permission management](web/permissions.md)
* [Usage of PostgreSQL database](web/postgresql_setup.md)
* [How to deal with false positives](analyzer/false_positives.md)
* [Store Cppcheck analyzer reports](/tools/report-converter/README.md#cppcheck)

# Install guide

## Linux

For a detailed dependency list, and for instructions
on how to install newer clang and clang-tidy versions
please see [Requirements](deps.md).
The following commands are used to bootstrap CodeChecker on Ubuntu 18.04 LTS:

```sh
# Install mandatory dependencies for a development and analysis environment.
# NOTE: clang or clang-tidy can be replaced by any later versions of LLVM/Clang.
sudo apt-get install clang clang-tidy build-essential curl doxygen gcc-multilib \
      git python-virtualenv python3-dev

# Check out CodeChecker source code.
git clone https://github.com/Ericsson/CodeChecker.git --depth 1 ~/codechecker
cd ~/codechecker

# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install a CodeChecker package.
make package

# For ease of access, add the build directory to PATH.
export PATH="$PWD/build/CodeChecker/bin:$PATH"

cd ..
```

**Note**: By default `make package` will build ldlogger shared objects for
`32bit` and `64bit` too. If you would like to build and package `64 bit only`
shared objects and ldlogger binary you can set `BUILD_LOGGER_64_BIT_ONLY`
environment variable to `YES` before the package build:
`BUILD_LOGGER_64_BIT_ONLY=YES make package`.

### Upgrading environment after system or Python upgrade

If you have upgraded your system's Python to a newer version (e.g. from
`2.7.6` to `2.7.12` &ndash; this is the case when upgrading Ubuntu from
14.04.2 LTS to 16.04.1 LTS), the installed environment will not work
out-of-the-box. To fix this issue, run the following command to upgrade your
`checker_env` too:

```sh
cd ~/codechecker/venv
virtualenv -p /usr/bin/python3 .
```

## Mac OS X

In OSX environment the intercept-build tool from
[scan-build](https://github.com/rizsotto/scan-build) is used to log the
compiler invocations.

It is possible that the [intercept-build can not
log](https://github.com/rizsotto/scan-build#limitations)
the compiler calls without turning off *System Integrity Protection (SIP)*.
`intercept build` can automatically detect if SIP is turned off.

You can turn off SIP on El Capitan this way:

  * Click the  (Apple) menu.
  * Select Restart...
  * Hold down command-R to boot into the Recovery System.
  * Click the Utilities menu and select Terminal.
  * Type csrutil disable and press return.
  * Close the Terminal app.
  * Click the  (Apple) menu and select Restart....

The following commands are used to bootstrap CodeChecker on
OS X El Capitan 10.11, macOS Sierra 10.12 and macOS High Sierra 10.13.

```sh
# Download and install dependencies.
brew update
brew install doxygen gcc git
pip3 install virtualenv

# Install the latest clang see: https://formulae.brew.sh/formula/llvm
brew install llvm@7

# Fetch source code.
git clone https://github.com/Ericsson/CodeChecker.git --depth 1 ~/codechecker
cd ~/codechecker

# Create a Python virtualenv and set it as your environment.
make venv_osx
source $PWD/venv/bin/activate

# Build and install a CodeChecker package.
make package

# For ease of access, add the build directory to PATH.
export PATH="$PWD/build/CodeChecker/bin:$PATH"

cd ..
```


## Docker
To run CodeChecker server in Docker see the [Docker](web/docker.md) documentation.

[![Docker](images/docker.jpg)](https://hub.docker.com/r/codechecker/codechecker-web)

# Check your first project

## Configuring Clang version

_Clang_ and/or _Clang-Tidy_ must be available on your system before you can
run analysis on a project. CodeChecker automatically detects and uses the
latest available version in your `PATH`.

If you wish to use a custom `clang` or `clang-tidy` binary, e.g. because you
intend to use a specific version or a specific build, you need to configure
the installed CodeChecker package to use the appropriate binaries. Please edit
the configuration file
`~/codechecker/build/CodeChecker/config/package_layout.json`. In the
`runtime/analyzers` section, you must set the values, as shown below, to the
binaries you intend to use.

```json
"analyzers" : {
  "clangsa" : "/path/to/clang/bin/clang-8",
  "clang-tidy" : "/path/to/clang/bin/clang-tidy-8"
},
```

You can set the `CC_ANALYZERS_FROM_PATH` environment variable before running a
CodeChecker command to `yes` or `1` to enforce taking the analyzers from the
`PATH` instead of the given binaries. If this option is set you can also
configure the plugin directory of the Clang Static Analyzer by using the
`CC_CLANGSA_PLUGIN_DIR` environment variable.

Make sure that the required include paths are at the right place!
Clang based tools search by default for
[builtin-includes](https://clang.llvm.org/docs/LibTooling.html#builtin-includes)
in a path relative to the tool binary.
`$(dirname /path/to/tool)/../lib/clang/8.0.0/include`

## Setting up the environment in your Terminal

These steps must always be taken in a new command prompt you wish to execute
analysis in.

```sh
source ~/codechecker/venv/bin/activate

# Path of CodeChecker package
# NOTE: SKIP this line if you want to always specify CodeChecker's full path.
export PATH=~/codechecker/build/CodeChecker/bin:$PATH

# Path of `scan-build.py` (intercept-build)
# NOTE: SKIP this line if you don't want to use intercept-build.
export PATH=~/<user path>/llvm/tools/clang/tools/scan-build-py/bin:$PATH

# Path of the built LLVM/Clang
# NOTE: SKIP this line if clang is available in your PATH as an installed Linux package.
export PATH=~/<user path>/build/bin:$PATH
```

## Check the test project

Analyze your project with the `check` command:

    CodeChecker check -b "cd ~/your-project && make clean && make" -o ~/results

`check` will print an overview of the issues found in your project by the
analyzers.

Start a CodeChecker web and storage server in another terminal or as a
background process. By default it will listen on `localhost:8001`.

The SQLite database containing the reports will be placed in your workspace
directory (`~/.codechecker` by default), which can be provided via the `-w`
flag.

    CodeChecker server

Store your analysis reports onto the server to be able to use the Web Viewer.

    CodeChecker store ~/results -n my-project


## View results

Open the [CodeChecker Web Viewer](http://localhost:8001) in your browser, and
you should be greeted with a web application showing you the analysis results.

# Important limitations with older Clang versions

Clang `3.6` or earlier releases are **NOT** supported due to CodeChecker
relying on features not available in those releases.

If you have Clang `3.7` installed you might see the following warning message:

> Hash value wasn't found in the plist file.

 * Use Clang `>= 3.8` or trunk `r251011` &mdash; otherwise CodeChecker
   generates a simple hash based on the filename and the line content. This
   method is applied for Clang-Tidy results too, because Clang-Tidy does not
   support bug identifier hash generation currently.

# Code Analyzers supported by CodeChecker
CodeChecker can only execute two main `C/C++` static analyzer tools:
- [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)
- [Clang Static Analyzer](https://clang-analyzer.llvm.org/)

However it can store the results of other analyzer tools in the database.
So it can be used as a generic tool for visualizing analyzer results.

For now CodeChecker supports the storage of the following analyzers results:

| Language       | Analyzer     |
| -------------- |--------------|
| **C/C++**      | [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)  |
|                | [Clang Static Analyzer](https://clang-analyzer.llvm.org/)    |
|                | [Cppcheck](/tools/report-converter/README.md#cppcheck)    |
|                | [Clang Sanitizers](supported_code_analyzers.md#clang-sanitizers)    |
|                | [Facebook Infer](/tools/report-converter/README.md#fbinfer)    |
| **Java**       | [SpotBugs](/tools/report-converter/README.md#spotbugs)    |
|                | [Facebook Infer](/tools/report-converter/README.md#fbinfer)    |
| **Python**     | [Pylint](/tools/report-converter/README.md#pylint)    |
|                | [Pyflakes](/tools/report-converter/README.md#pyflakes)    |
| **JavaScript** | [ESLint](/tools/report-converter/README.md#eslint)    |
| **TypeScript** | [TSLint](/tools/report-converter/README.md#tslint)    |
| **Go**         | [Golint](/tools/report-converter/README.md#golint)    |


We are planning to support the storage of the results created by other
analyzers for different languages (Java, Python ...). For more detailed
information check out the
[supported code analyzers](supported_code_analyzers.md) documentation.

# Useful Documentation

## Feature overview

* [CodeChecker feature overview](feature_comparison.md)

## Deployment

* [Deploy server using docker](web/docker.md#deployment)

## Static analysis

* [False Positives](analyzer/false_positives.md)
* [Checker and Static Analyzer configuration](analyzer/checker_and_analyzer_configuration.md)
* [Checker documentation](web/checker_docs.md)
* [GCC incompatibilities](analyzer/gcc_incompatibilities.md)

## Security configuration
* [Authentication](web/authentication.md)
* [Permissions](web/permissions.md)

## Continuous Integration (CI)
* [Jenkins Gerrit integration](jenkins_gerrit_integration.md)
* [Daily Scripts](script_daily.md)

## Database configuration
* [PostgreSQL setup](web/postgresql_setup.md)
* [Schema Guide](web/db_schema_guide.md)

## Server configuration
* [Products](web/products.md)
* [Logging](logging.md)

## Developer documentations
* [Architecture](architecture.md)
* [Package layout](package_layout.md)
* [Dependencies](deps.md)
* [Thrift interface](web/api/README.md)
* [Package and integration tests](tests.md)

## Conference papers, presentations
* A high-level overview about the infrastructure is available amongst the
  [2015Euro LLVM Conference](http://llvm.org/devmtg/2015-04) presentations.<br/>
  **Dániel KRUPP, György ORBÁN, Gábor HORVÁTH and Bence BABATI**:<br/>
  [_Industrial Experiences with the Clang Static Analysis Toolset_](http://llvm.org/devmtg/2015-04/slides/Clang_static_analysis_toolset_final.pdf)
