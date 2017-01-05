[![Build status](https://travis-ci.org/Ericsson/codechecker.png?branch=master)](https://travis-ci.org/Ericsson/codechecker)

CodeChecker
===========

**CodeChecker** is a static analysis infrastructure built on the [LLVM/Clang
Static Analyzer](http://clang-analyzer.llvm.org) toolchain, replacing
[`scan-build`](http://clang-analyzer.llvm.org/scan-build.html) in a Linux or
macOS (OS X) development environment.


![CodeChecker web interface for viewing discovered code defects](docs/images/viewer.png)


Main features
-------------

  * Support for multiple analyzers, currently _Clang Static Analyzer_ and
    _Clang-Tidy_
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
  * Suppression of known false positive results, either in configuration file
    or via annotation in source code, along with exclusion of entire source
    paths from analysis
  * `quickcheck` mode shows analysis results on standard output
  * Easily implementable [Thrift](http://thrift.apache.org)-based
    server-client communication used for storing and querying of discovered
    defects
  * Support for multiple bug visualisation frontends, such as the web
    application, a [command-line tool](docs/usage.md) and an [Eclipse
    plugin](http://github.com/Ericsson/CodeCheckerEclipsePlugin)


A high-level overview about the infrastructure is available amongst the [2015
Euro LLVM Conference](http://llvm.org/devmtg/2015-04) presentations.<br/>
**Dániel KRUPP, György ORBÁN, Gábor HORVÁTH and Bence BABATI**:<br/>
[_Industrial Experiences with the Clang Static Analysis Toolset_](http://llvm.org/devmtg/2015-04/slides/Clang_static_analysis_toolset_final.pdf)

Install
-------

### Linux

For a detailed dependency list, please see [Requirements](docs/deps.md). The
following commands are used to bootstrap CodeChecker on Ubuntu 14.04.2 LTS:

~~~{.sh}
# Install mandatory dependencies for a development and analysis environment
# NOTE: clang-3.6 can be replaced by any later versions of LLVM/Clang
sudo apt-get install clang-3.6 build-essential doxygen gcc-multilib git \
  python-virtualenv python-dev thrift-compiler wget

# Create a Python virtualenv and set it as your environment
virtualenv -p /usr/bin/python2.7 ~/checker_env
source ~/checker_env/bin/activate

# Check out CodeChecker
git clone https://github.com/Ericsson/CodeChecker.git --depth 1
cd codechecker

# Install the basic Python modules needed for operation
pip install -r .ci/basic_python_requirements

# Build and install a CodeChecker package
./build_package.py -o ~/codechecker_package

# For ease of access, add the install directory for PATH
export PATH="~/codechecker_package/CodeChecker/bin:$PATH"

cd ..
~~~

### Mac OS X

The following commands are used to bootstrap CodeChecker on OS X El Capitan
10.11.5 and macOS Sierra 10.12 Beta.

On El Capitan System Integrity Protection (SIP) needs to be turned off:
  * Click the  (Apple) menu.
  * Select Restart...
  * Hold down command-R to boot into the Recovery System.
  * Click the Utilities menu and select Terminal.
  * Type csrutil disable and press return.
  * Close the Terminal app.
  * Click the  (Apple) menu and select Restart....

Check out and build LLVM/Clang with extra tools. Follow the [Get Started with
LLVM/Clang](http://clang.llvm.org/get_started.html) documentation.

~~~{.sh}
# Download and install dependencies
brew update
brew install doxygen thrift gcc git

# Fetch source code
git clone https://github.com/tmsblgh/codechecker-osx-migration.git
cd codechecker

# Install required basic python modules
pip install -r .ci/basic_python_requirements

# Create codechecker package
./build_package.py -o ~/codechecker_package
cd ..
~~~

Check your first project
------------------------

### Testing and configuring LLVM/Clang availability

_Clang_ and/or _Clang-Tidy_ must be available on your system before you can
run analysis on a test project. The binaries are usually named `clang` or
`clang-3.6` (and `clang-tidy` or `clang-tidy-3.6`, respectively), but this
depends on your Linux distribution.


    which clang-3.6
    which clang-tidy-3.6


If `clang` or `clang-tidy` is not an available command, you must configure the
installed CodeChecker package to use the appropriate binaries for analysis.
Edit the configuration file
`~/codechecker_package/CodeChecker/config/package_layout.json`. In the
`runtime/analyzers` section, you must set the values, as shown below, to the
clang binaries available in your `PATH`.

~~~{.json}
"analyzers" : {
  "clangsa" : "clang-3.6",
  "clang-tidy" : "clang-tidy-3.6"
},
~~~

### Setting up the environment in your Terminal

These steps must always be taken in a new command prompt you wish to execute
analysis in.

~~~{.sh}
source ~/checker_env/bin/activate

# Path of CodeChecker package
# NOTE: SKIP this line if you want to always specify CodeChecker's full path
export PATH=~/codechecker_package/CodeChecker/bin:$PATH

# Path of `scan-build.py` (intercept-build)
# NOTE: SKIP this line if you don't want to use intercept-build
export PATH=~/{user path}/llvm/tools/clang/tools/scan-build-py/bin:$PATH

# Path of the built LLVM/Clang
# NOTE: SKIP this line if clang is available in your PATH as an installed Linux package
export PATH=~/{user path}/build/bin:$PATH
~~~

### Check the test project

Check your project using SQLite database. The database will be placed in your
workspace directory (`~/.codechecker` by default), which can be provided via
the `-w` flag.


    CodeChecker check -n test-check -b "cd ~/your-project && make clean && make"


### Start a web server


    CodeChecker server


### View results

Open the [CodeChecker Web Viewer](http://localhost:8001) in your browser, and
you should be greeted with a web application showing you the analysis results.

Known important limitations
---------------------------

CodeChecker requires some new features from LLVM/Clang to work properly.

If your installed Clang does not support these features you will see the
following debug messages in your log:

> Check name wasn't found in the plist file.

Use clang `>= 3.7` or trunk `r228624` &mdash; otherwise CodeChecker makes a
guess based on the report message

> Hash value wasn't found in the plist file.

Use clang `>= 3.8` or trunk `r251011` &mdash; otherwise CodeChecker generates
a simple hash based on the filename and the line content. This method is
applied for Clang-Tidy results too, because Clang-Tidy does not support
bug identifier hash generation currently


Additional documentation
------------------------

  * [User guide](docs/user_guide.md)
  * [Requirements, external source dependencies](docs/deps.md)
  * [Architecture overview](docs/architecture.md)
  * [Package layout](docs/package_layout.md)
  * [Checker documentation](docs/checker_docs.md)
  * [Thrift interface](thrift_api/thrift_api.md)
  * [Package and integration tests](tests/functional/package_test.md)
  * [Database schema migration](docs/db_schema_guide.md)
  * [Usage of PostgreSQL database](docs/postgresql_setup.md)
  * [Requiring credentials to view analysis results](docs/authentication.md)
