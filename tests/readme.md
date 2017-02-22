# How to run the tests

## Rrequirements

Additionaly to the package building requirements the python nosetest running framework is required.

~~~~~~{.sh}
# create and source python virtualenv for development
make venv_dev
source venv/bin/activate
~~~~~~

## Running the tests

~~~~~~{.sh}
# run all the tests
make tests

# run only the unittests
make test_unit

# run only the functional tests
make test_functional

# do not use PostgreSQL for running the tests (SQLite will be used)
make test_sqlite


# remove the build and test directories
~~~~~~{.sh}
make clean
~~~~~~

### Testing with PostgresSQL database backend

# run tests with PostgresSQL
~~~~~~{.sh}
make test_psql
~~~~~~

At least one of the database drivers needs to be available to use the PostgreSQL database backend.  
Psycopg2 is used by default if not found pg8000 is used.
