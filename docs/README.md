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

**:bulb: Check out our [DEMO](https://codechecker-demo.eastus.cloudapp.azure.com) showing some analysis results of open-source projects!**

# Main features
## Command line C/C++ Analysis
  * Executes [_Clang-Tidy_](http://clang.llvm.org/extra/clang-tidy/) and [_Clang Static Analyzer_](http://clang-analyzer.llvm.org/) with Cross-Translation Unit analysis, Statistical Analysis (when checkers are available).
  * Creates the JSON compilation database by wirtapping any build process (e.g. `CodeChecker log -b "make"`)
  * Automatically analyzes gcc cross-compiled projects: detecting GCC or Clang compiler configuration and forming the corresponding clang analyzer invocations
  * Incremental analysis: only the changed files and its dependencies need to be reanalized
  * False positive suppression with a possibility to add review comments
  * Result visualization in command line or in static HTML

## Web based report storage
  * **You can store & visualize thousands of analysis reports** of many analyzers like
    Clang Static Analyzer (C/C++), Clang Tidy (C/C++), Facebook Infer (C/C++, Java), Clang Sanitizers (C/C++), Spotbugs (Java), Pylint (Python), Eslint (Javascript) ...  
    For a complete list see [Supported Analyzers](supported_code_analyzers.md)
  * **Web application** for viewing discovered code defects with a streamlined,
    easy experience (with PostgreSQL, or SQLite backend)
  * **Gerrit and GitLab integration** Shows analysis results as [Gitlab](gitlab_integration.md) or [Gerrit](jenkins_gerrit_integration.md) reviews
  * **Filterable** (defect checker name, severity, source paths, ...) and
    **comparable** (calculates difference between two analyses of the project,
    showing which bugs have been fixed and which are newly introduced) result
    viewing
  * **Diff mode:** Shows the list of bugs that have been introduced since your last analyzer
    execution
  * Results can be shared with fellow developers, the **comments** and
    **review** system helps communication of code defects
  * Easily implementable [Thrift](http://thrift.apache.org)-based
    server-client communication used for storing and querying of discovered
    defects
  * Support for multiple bug visualisation frontends, such as the web
    application, a [command-line tool](usage.md) and an
    [Eclipse plugin](http://github.com/Ericsson/CodeCheckerEclipsePlugin)


# User documentation

* [Getting started (How-To with examples)](usage.md)

## C/C++ Analysis
* [Analyzer User guide](analyzer/user_guide.md)
* [Avoiding or suppressing false positives](analyzer/false_positives.md)
* [Checker and Static Analyzer configuration](analyzer/checker_and_analyzer_configuration.md)
* [GCC incompatibilities](analyzer/gcc_incompatibilities.md)
* [Suppressing false positives](analyzer/user_guide.md#source-code-comments)

## Web based report management
* [Webserver User Guide](web/user_guide.md)
* [WEB GUI User Guide](/web/server/www/userguide/userguide.md)
* [Command line and WEB UI Feature overview](feature_comparison.md)
* Security configuration 
  * [Configuring Authentication](web/authentication.md)
  * [Configuring Authorization](web/permissions.md)
* Deployment
  * [Deploy server using docker](web/docker.md#deployment)
* Server Configuration
  * [Configuring Server Logging](logging.md)
  * [Setting up multiple CodeChecker repositories in one server](web/products.md)
* Continous Integration(CI)
  * [Setting up CI gating with Gerrit and Jenkins](jenkins_gerrit_integration.md)
* Database Configuration
  * [PostgreSQL database backend setup guide](web/PostgreSQL_setup.md)
  * [CodeChecker server and database schema upgrade guide](web/db_schema_guide.md)

### Storage of reports from analyzer tools
CodeChecker can be used as a generic tool for visualizing analyzer results.

The following tools are supported:

| Language       | Analyzer     |
| -------------- |--------------|
| **C/C++**      | [Clang Static Analyzer](https://clang-analyzer.llvm.org/)    |
|                | [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)  |
|                | [Clang Sanitizers](supported_code_analyzers.md#clang-sanitizers)    |
|                | [Cppcheck](/tools/report-converter/README.md#cppcheck)    |
|                | [Facebook Infer](/tools/report-converter/README.md#facebook-infer)    |
|                | [Coccinelle](/tools/report-converter/README.md#coccinelle)    |
|                | [Smatch](/tools/report-converter/README.md#smatch)    |
|                | [Kernel-Doc](/tools/report-converter/README.md#kernel-doc)    |
| **Java**       | [SpotBugs](/tools/report-converter/README.md#spotbugs)    |
|                | [Facebook Infer](/tools/report-converter/README.md#fbinfer)    |
| **Python**     | [Pylint](/tools/report-converter/README.md#pylint)    |
|                | [Pyflakes](/tools/report-converter/README.md#pyflakes)    |
| **JavaScript** | [ESLint](/tools/report-converter/README.md#eslint)    |
| **TypeScript** | [TSLint](/tools/report-converter/README.md#tslint)    |
| **Go**         | [Golint](/tools/report-converter/README.md#golint)    |
| **Markdown**   | [Markdownlint](/tools/report-converter/README.md#markdownlint)    |
|                | [Sphinx](/tools/report-converter/Readme.md#sphinx)    |


For details see 
[supported code analyzers](supported_code_analyzers.md) documentation and the 
[Report Converter Tool](/tools/report-converter/README.md).

## Common Tools
Useful tools that can also be used outside CodeChecker.

* [Build Logger (to generate JSON Compilation Database from your builds)](/analyzer/tools/build-logger/README.md)
* [Plist to HTML converter (to generate HTML files from the given plist files)](/tools/plist_to_html/README.md)
* [Report Converter Tool (to convert analysis results from other analyzers to the codechecker report directory format))](/tools/report-converter/README.md)
* [Translation Unit Collector (to collect source files of a translation unit or to get source files which depend on the given header files)](/tools/tu_collector/README.md)
* [Report Hash generator (to generate unique hash identifiers for reports)](/tools/codechecker_report_hash/README.md)

## Helper Scripts
* [Helper Scripts for daily analysis](script_daily.md)

# Install guide

## Linux

For a detailed dependency list, and for instructions on how to install newer
Clang and Clang-Tidy versions, please see [Requirements](deps.md).
The following commands are used to bootstrap CodeChecker on Ubuntu 20.04 LTS:

```sh
# Install mandatory dependencies for a development and analysis environment.
# NOTE: clang or clang-tidy can be any sufficiently fresh version, and need not
#       come from package manager!
sudo apt-get install clang clang-tidy build-essential curl doxygen gcc-multilib \
      git python3-virtualenv python3-dev

# Install nodejs dependency for web. In case of Debian/Ubuntu you can use the
# following commands. For more information see the official docs:
# https://nodejs.org/en/download/package-manager/
curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash -
sudo apt-get install -y nodejs

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

**Notes**:
- By default `make package` will build ldlogger shared objects for
`32bit` and `64bit` too. If you would like to build and package `64 bit only`
shared objects and ldlogger binary you can set `BUILD_LOGGER_64_BIT_ONLY`
environment variable to `YES` before the package build:
`BUILD_LOGGER_64_BIT_ONLY=YES make package`.
- By default the `make package` will build the UI code if it's not built yet
or the UI code is changed. If you wouldn't like to build the UI code you can
set the `BUILD_UI_DIST` environment variable to `NO` before the package build:
`BUILD_UI_DIST=NO make package`.

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
For installation instructions for Mac OS X see [Mac OS X Installation Guide](install_macosx.md) documentation.

## Docker
To run CodeChecker server in Docker see the [Docker](web/docker.md) documentation.
You can find the CodeChecker web-server containter at the [Docker Hub](https://hub.docker.com/r/codechecker/codechecker-web).

 <img src="https://raw.githubusercontent.com/Ericsson/codechecker/master/docs/images/docker.jpg" width="100">

# Analyze your first project

## Setting up the environment in your Terminal

These steps must always be taken in a new command prompt you wish to execute
analysis in.

```sh
source ~/codechecker/venv/bin/activate

# Path of CodeChecker package
# NOTE: SKIP this line if you want to always specify CodeChecker's full path.
export PATH=~/codechecker/build/CodeChecker/bin:$PATH

# Path of the built LLVM/Clang
# NOTE: SKIP this line if clang is available in your PATH as an installed Linux package.
export PATH=~/<user path>/build/bin:$PATH
```
## Execute analysis

Analyze your project with the `check` command:

    CodeChecker check -b "cd ~/your-project && make clean && make" -o ./results

`check` will print an overview of the issues found in your project by the
analyzers. The reports will be stored in the `./results` directory in `plist` 
XML format.

## Export the reports as static HTML files
You can visualize the results as static HTML by executing

`CodeChecker parse -e html ./results -o ./reports_html`

An index page will be generated with a list of all repors in 
`./reports_html/index.html` 


## Optionally store the results in Web server & view the results

If you have hundreds of results, you may want to store them on the web
server with a database backend.

Start a CodeChecker web and storage server in another terminal or as a
background process. By default it will listen on `localhost:8001`.

The SQLite database containing the reports will be placed in your workspace
directory (`~/.codechecker` by default), which can be provided via the `-w`
flag.

    CodeChecker server

Store your analysis reports onto the server to be able to use the Web Viewer.

    CodeChecker store ./results -n my-project

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


## Developer documentations
* [Architecture](architecture.md)
* [Package layout](package_layout.md)
* [Dependencies](deps.md)
* [Thrift interface](web/api/README.md)
* [Package and integration tests](tests.md)
* [Checker documentation mapping file](web/checker_docs.md)

## Conference papers, presentations
* A high-level overview about the infrastructure is available amongst the
  [2015Euro LLVM Conference](http://llvm.org/devmtg/2015-04) presentations.<br/>
  **Dániel KRUPP, György ORBÁN, Gábor HORVÁTH and Bence BABATI**:<br/>
  [_Industrial Experiences with the Clang Static Analysis Toolset_](http://llvm.org/devmtg/2015-04/slides/Clang_static_analysis_toolset_final.pdf)
