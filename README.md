
[![Build Status](https://travis-ci.org/Ericsson/codechecker.svg?branch=master)](https://travis-ci.org/Ericsson/codechecker)
-----
# Introduction
CodeChecker is a static analysis infrastructure built on [Clang Static Analyzer](http://clang-analyzer.llvm.org/).  

CodeChecker replaces [scan-build](http://clang-analyzer.llvm.org/scan-build.html) in Clang Static Analyzer in Linux systems.

It provides
 * a new command line tool for analyzing projects
 * dynamic web based defect viewer (instead of static html)
 * a PostgreSQL/SQLite based defect storage & management
 * incremental bug reporting (show only new bugs compared to a baseline)
 * suppression of false positives
 * better integration with build systems (through the LD_PRELOAD mechanism)
 * Thrift API based server-client model for storing bugs and viewing results.
 * It is possible to connect multiple bug viewers. Currently a web-based viewer and a command line viewer are provided.

You can find a high level overview about the infrastructure in the presentation
at the [2015 Euro LLVM](http://llvm.org/devmtg/2015-04/) Conference:

__Industrial Experiences with the Clang Static Analysis Toolset  
_Daniel Krupp, Gyorgy Orban, Gabor Horvath and Bence Babati___ ([ Slides](http://llvm.org/devmtg/2015-04/slides/Clang_static_analysis_toolset_final.pdf))

## Important Limitations
CodeChecker requires some new features from clang to work properly.
If your clang version does not have these features you will see warning messages like these during the check:


  * `Check name wasn't found in the plist file.` --> use clang = 3.7 or trunk@r228624; otherwise CodeChecker makes a guess based on the report message
  * `Hash value wasn't found in the plist file.` --> wait for a newer clang version; otherwise CodeChecker generates a simple hash based on the filename and the line content

## Linux
### Packaging requirements
  *  [Git](https://git-scm.com/) (> 1.9.1)  
  *  [Thrift compiler](https://thrift.apache.org/) (> 0.9.2)  

        required to generate python and javascript files
  *  [Doxygen](http://www.stack.nl/~dimitri/doxygen/) (> 1.8)  

     markdown support is required  
  *  Build-logger

     ld-logger is used to create a build log from the build commands.
     It is possible to build package without ld-logger.
     In that case no automatic compilation logging is available.  
     There should be already an existing file containing the compilation commands (in `cmake` with the 'CMAKE_EXPORT_COMPILE_COMMANDS' option) to run the static analyzer.
     To build ld-logger 32 and 64 bit versions `gcc multilib` and `make`
     is required

  * Other external dependencies are automatically downloaded and
    copied to the necessary directories in the package.
    Additional runtime requirements are described in the next external source
    dependencies section.

### Runtime requirements
  *  [Clang Static analyzer](http://clang-analyzer.llvm.org/) (latest stable or [trunk](http://clang.llvm.org/get_started.html))
  *  [PostgreSQL](http://www.postgresql.org/ "PostgreSQL") (> 9.3.5) (optional)
  *  [Python2](https://www.python.org/) (> 2.7)
  *  [Alembic](https://pypi.python.org/pypi/alembic) (>=0.8.2)
  *  [SQLAlchemy](http://www.sqlalchemy.org/) (> 1.0.2)
     - [PyPi SQLAlchemy](https://pypi.python.org/pypi/SQLAlchemy) (> 1.0.2)
  *  [psycopg2](http://initd.org/psycopg/ "psycopg2") (> 2.5.4) or [pg8000](https://github.com/mfenniak/pg8000 "pg8000") (>= 1.10.0) (optional)
     - [PyPi psycopg2](https://pypi.python.org/pypi/psycopg2/2.6.1) __requires lbpq!__
     - [PyPi pg8000](https://pypi.python.org/pypi/pg8000)
  * Thrift python modules
     +  [PyPi thrift](https://pypi.python.org/pypi/thrift/0.9.2)(> 0.9.2 )

### Install & setup
Tested on Ubuntu LTS 14.04.2
~~~~~~{.sh}

# get ubuntu packages
sudo apt-get install clang-3.6 libpq-dev postgresql postgresql-client-common postgresql-common doxygen build-essential thrift-compiler python-virtualenv python-dev gcc-multilib git wget

# Note: The following PostgreSQL specific steps are only needed when PostgreSQL
# is used for checking. By default CodeChecker uses SQLite.

# setup database for a test_user
sudo -i -u postgres
# add a test user with "test_pwd" password
createuser --createdb --login --pwprompt test_user
exit

# PostgreSQL authentication
# PGPASSFILE environment variable should be set to a pgpass file
# For format and further information see PostgreSQL documentation:
# http://www.postgresql.org/docs/current/static/libpq-pgpass.html

echo "*:5432:*:test_user:test_pwd" >> ~/.pgpass
chmod 0600 ~/.pgpass

# create new python virtualenv
virtualenv -p /usr/bin/python2.7 ~/checker_env
# activate virtualenv
source ~/checker_env/bin/activate


# get source code
git clone https://github.com/Ericsson/codechecker.git
cd codechecker
# install required python modules
pip install -r .ci/python_requirements
# create codechecker package
./build_package.py -o ~/codechecker_package
cd ..
~~~~~~


### Check a test project
~~~~~~{.sh}

# check if clang is available
which clang

# if 'clang' command is not available the package can be configured to use
# another clang binary for checking like 'clang-3.6'
# edit the 'CodeChecker/config/package_layout.json' config file "runtime"
# section in the generated package and extend it with a new config option
# '"compiler_bin" : "clang-3.6",'

# activate virtualenv
source ~/checker_env/bin/activate

# directory to store temporary files during the static analysis
mkdir ~/checker_workspace

# add bin directory to PATH. This step can be skipped if you always give the path of CodeChecker command.
export PATH=~/codechecker_package/CodeChecker/bin:$PATH

# check the project using SQLite. The database is placed in the working
# directory which can be provided by -w flag (~/.codechecker by default).
CodeChecker check -n test_project_check -b "cd my_test_project && make clean && make"

# alternatively check project using the postgresql database port and the newly
# created db user
# When using sqlite, the database settings are unnecessary
CodeChecker check --dbusername test_user --postgresql --dbport 5432 -n test_project_check -b "cd my_test_project && make clean && make"

~~~~~~

### Start the viewer Web server
~~~~~~{.sh}

# activate virtualenv
source ~/checker_env/bin/activate

# source codechecker
source ~/codechecker_package/CodeChecker/init/init.sh

# start web server on port 8080 on localhost only
CodeChecker server --dbusername test_user --dbport 5432 -w ~/checker_workspace -v 8080

#check results with firefox
#firefox http://localhost:8080

~~~~~~
If all goes well you can check analysis results in your web browser:

![CodeChecker Viewer](https://raw.githubusercontent.com/Ericsson/codechecker/master/docs/images/viewer.png)

See user guide for further configuration and check options

##Additional documentations
[User guide](docs/user_guide.md)

[Checker documentation](docs/checker_docs.md)

[Package layout](docs/package_layout.md)

[Thrift api](thrift_api/thrift_api.md)

[External source dependencies](docs/deps.md)

[Test documentation](tests/package_test.md)

[Database schema migration](docs/db_schema_guide.md)
