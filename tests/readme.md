# How to run the tests

## Rrequirements

Additionaly to the package building requirements the python nosetest running framework is required.

~~~~~~{.sh}
# source the already created python virtualenv for package building
source ~/checker_env/bin/activate

# install nosetest
pip install nose
~~~~~~

## Running the tests

To run the tests call the run_test.sh script.
It will build a package, and run the all the unit and functional tests.
~~~~~~{.sh}
run_tests.sh
~~~~~~

## More detailed test running
~~~~~~{.sh}
# setup some required environment variables to run the tests
# create temporary directories
source tests/test_env_setup.sh

# build the CodeChecker package
build_package.py -o $TEST_CODECHECKER_PACKAGE_DIR -v

# do not use PostgreSQL for running the tests (SQLite will be used)
export TEST_USE_POSTGRESQL=false

# run all the tests
nosetests tests

# run only the unittests
nosetests tests/unit

# run only the functional tests
nosetests tests/functional

# remove the temporary directories and unset the environment variables
# set by sourcing the test_env_setup.sh script
clean_tests.sh
~~~~~~

### Testing with PostgresSQL database backend

To run the tests with PostgreSQL backend set these environment variables:
~~~~~~{.sh}
export TEST_USE_POSTGRESQL=true
~~~~~~

Multiple PostgreSQL database drivers are supported (psycopg2, pg8000).  
Select explicitly a database driver to used for testing.
~~~~~~{.sh}
export CODECHECKER_DB_DRIVER=psycopg2
~~~~~~

At least one of the database drivers needs to be available to use the PostgreSQL database backend.  
Psycopg2 is used by default if not found pg8000 is used.
