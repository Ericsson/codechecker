
## PostgreSQL

## Extra runtime requirements for PostgreSQL database support
  *  [PostgreSQL](http://www.postgresql.org/ "PostgreSQL") (> 9.3.5) (optional)
  *  [psycopg2](http://initd.org/psycopg/ "psycopg2") (> 2.5.4) or [pg8000](https://github.com/mfenniak/pg8000 "pg8000") (>= 1.10.0) at least one database connector is required for postgreSQL database support (both are supported)
     - [PyPi psycopg2](https://pypi.python.org/pypi/psycopg2/2.6.1) __requires lbpq!__
     - [PyPi pg8000](https://pypi.python.org/pypi/pg8000)

## Install & setup additional dependencies
Tested on Ubuntu LTS 14.04.2
~~~~~~{.sh}

# get the extra postgresql packages
sudo apt-get install libpq-dev python-dev postgresql postgresql-client-common postgresql-common

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

# activate the already created virtualenv in the basic setup
source ~/checker_env/bin/activate

# install required python modules
pip install -r .ci/python_requirements

# create codechecker package
./build_package.py -o ~/codechecker_package
cd ..
~~~~~~

## Run CodeChecker

Activate virtualenv.
~~~~~~{.sh}
source ~/checker_env/bin/activate
~~~~~~

Add package bin directory to PATH.
This step can be skipped if you always give the path of CodeChecker command.
~~~~~~{.sh}
export PATH=~/codechecker_package/CodeChecker/bin:$PATH
~~~~~~

Check a test project.
~~~~~~{.sh}
CodeChecker check --dbusername test_user --postgresql -n test_project_check -b "cd my_test_project && make clean && make"
~~~~~~

Start web server to view the results.
~~~~~~{.sh}
CodeChecker server --dbusername test_user --postgresql
~~~~~~

View the results with firefox.
~~~~~~{.sh}
firefox http://localhost:8001
~~~~~~
