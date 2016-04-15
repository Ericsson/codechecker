#!/usr/bin/env bash

. tests/test_env_setup.sh

./build_package.py -o $TEST_CODECHECKER_PACKAGE_DIR -v

nosetests tests/test_packages/
