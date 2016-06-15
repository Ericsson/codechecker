#!/usr/bin/env bash

which nosetests || (echo "[ERROR] nosetests framework is needen to run the tests" && exit 1)
which clang || (echo "[ERROR] clang required to run functional tests" && exit 1)

# setup environment variables, temporary directories
. tests/test_env_setup.sh || exit 1

# build the package used for the tests
./build_package.py -o $TEST_CODECHECKER_PACKAGE_DIR -v || exit 1

# run all the tests
nosetests tests/test_packages/

# cleanup the environment variables and temporary
# directories
./tests/clean_tests.sh

