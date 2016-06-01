#!/usr/bin/env bash

# setup environment variables, temporary directories
. tests/test_env_setup.sh

# build the package used for the tests
./build_package.py -o $TEST_CODECHECKER_PACKAGE_DIR -v

# run all the tests
nosetests tests/test_packages/

# cleanup the environment variables and temporary
# directories
clean_tests.sh

