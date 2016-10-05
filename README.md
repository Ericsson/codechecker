[![Build Status](https://travis-ci.org/Ericsson/codechecker.svg?branch=master)](https://travis-ci.org/Ericsson/codechecker)
-----
# Introduction
CodeChecker is a static analysis infrastructure built on [Clang Static Analyzer](http://clang-analyzer.llvm.org/).  

CodeChecker replaces [scan-build](http://clang-analyzer.llvm.org/scan-build.html) in Clang Static Analyzer in Linux systems.

Main features:
  * store the result of multiple large analysis run results efficiently
  * run multiple analyzers, currently Clang Static Analyzer and Clang-Tidy is supported
  * dynamic web based defect viewer
  * a PostgreSQL/SQLite based defect storage & management (both are optional, results can be shown on standard output in quickcheck mode)
  * update analyzer results only for modified files (depends on the build system)
  * compare analysis results (new/resolved/unresolved bugs compared to a baseline)
  * filter analysis results (checker name, severity, source file name ...)
  * skip analysis in specific source directories if required
  * suppression of false positives (in config file or in the source)
  * Thrift API based server-client model for storing bugs and viewing results.
  * It is possible to connect multiple bug viewers. Currently a web-based viewer and a command line viewer are provided.


You can find a high level overview about the infrastructure in the presentation
at the [2015 Euro LLVM](http://llvm.org/devmtg/2015-04/) Conference:

__Industrial Experiences with the Clang Static Analysis Toolset  
_Daniel Krupp, Gyorgy Orban, Gabor Horvath and Bence Babati___ ([ Slides](http://llvm.org/devmtg/2015-04/slides/Clang_static_analysis_toolset_final.pdf))

## Important Limitations
CodeChecker requires some new features from clang to work properly.
If your clang version does not have these features you will see in debug log the following messages:

  * `Check name wasn't found in the plist file.` --> use clang = 3.7 or trunk@r228624; otherwise CodeChecker makes a guess based on the report message
  * `Hash value wasn't found in the plist file.` --> update for a newer clang version; otherwise CodeChecker generates a simple hash based on the filename and the line content, this method is applied for Clang Tidy results too, because Clang Tidy does not support bug identifier hash generation currently

## Linux
For a more detailed dependency list see [Requirements](docs/deps.md)
### Basic dependecy install & setup
Tested on Ubuntu LTS 14.04.2
~~~~~~{.sh}

# get ubuntu packages
# clang-3.6 can be replaced by any later versions of clang
sudo apt-get install clang-3.6 doxygen build-essential thrift-compiler python-virtualenv gcc-multilib git wget

# create new python virtualenv
virtualenv -p /usr/bin/python2.7 ~/checker_env
# activate virtualenv
source ~/checker_env/bin/activate

# get source code
git clone https://github.com/Ericsson/codechecker.git
cd codechecker

# install required basic python modules
pip install -r .ci/basic_python_requirements

# create codechecker package
./build_package.py -o ~/codechecker_package
cd ..
~~~~~~

## OS X

### Basic dependecy install & setup
Tested on OS X El Capitan 10.11.5 & macOS Sierra 10.12 Beta
~~~~~~{.sh}

# on El Capitan System Integrity Protection (SIP) need to turn off
- Click the  (Apple) menu.
- Select Restart...
- Hold down command-R to boot into the Recovery System.
- Click the Utilities menu and select Terminal.
- Type csrutil disable and press return.
- Close the Terminal app.
- Click the  (Apple) menu and select Restart....

# check out and build clang with extra tools
How to: http://clang.llvm.org/get_started.html

# get dependencies
brew update
brew install doxygen thrift gcc git

# get source code
git clone https://github.com/tmsblgh/codechecker-osx-migration.git
cd codechecker

# install required basic python modules
pip install -r .ci/basic_python_requirements

# create codechecker package
./build_package.py -o ~/codechecker_package
cd ..
~~~~~~

### Check a test project
#### Check if clang or clang tidy is available
The installed clang binary names should be ```clang``` or ```clang-3.6``` which depends on your Linux distribution.
~~~~~~{.sh}
which clang-3.6
which clang-tidy-3.6
~~~~~~
If 'clang' or 'clang-tidy' commands are not available the package can be configured to use another/newer clang binary for the analysis.  
Edit the 'CodeChecker/config/package_layout.json' config files "runtime/analyzers"
section in the generated package and modify the analyzers section to the analyzers
available in the PATH
```
"analyzers" : {
  "clangsa" : "clang-3.6",
  "clang-tidy" : "clang-tidy-3.6"
  },
```

#### Activate virtualenv
~~~~~~{.sh}
source ~/checker_env/bin/activate
~~~~~~

#### Add package bin directory to PATH.
This step can be skipped if you always give the path of CodeChecker command.
~~~~~~{.sh}
export PATH=~/codechecker_package/CodeChecker/bin:$PATH
~~~~~~
Scan-build-py (intercept-build)
~~~~~~{.sh}
export PATH=~/{user path}/llvm/tools/clang/tools/scan-build-py/bin:$PATH
~~~~~~
Clang
~~~~~~{.sh}
export PATH=~/{user path}/build/bin:$PATH
~~~~~~

#### Check the project
Check the project using SQLite. The database is placed in the working
directory which can be provided by -w flag (~/.codechecker by default).
~~~~~~{.sh}
CodeChecker check -n test_project_check -b "cd my_test_project && make clean && make"
~~~~~~

#### Start web server to view the results
~~~~~~{.sh}
CodeChecker server
~~~~~~

#### View the results with firefox
~~~~~~{.sh}
firefox http://localhost:8001
~~~~~~

If all goes well you can check analysis results in your web browser:

![CodeChecker Viewer](https://raw.githubusercontent.com/Ericsson/codechecker/master/docs/images/viewer.png)

See user guide for further configuration and check options.

## Additional documentations

[User guide](docs/user_guide.md)

[Use with PostgreSQL database](docs/postgresql_setup.md)

[Command line usage_examples](docs/usage.md)

[Checker documentation](docs/checker_docs.md)

[Architecture overview](docs/architecture.md)

[Requirements](docs/deps.md)

[Package layout](docs/package_layout.md)

[Thrift api](thrift_api/thrift_api.md)

[External source dependencies](docs/deps.md)

[Test documentation](tests/functional/package_test.md)

[Database schema migration](docs/db_schema_guide.md)

[Privileged server and authentication in client](docs/authentication.md)