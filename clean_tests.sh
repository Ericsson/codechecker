#!/usr/bin/env bash

echo "Removing temporary directory created for testing: " $TEST_CODECHECKER_PACKAGE_DIR

rm -rf $TEST_CODECHECKER_PACKAGE_DIR

echo "Unsetting environment variables used for testing"
unset TEST_TESTS_DIR
unset TEST_CODECHECKER_PACKAGE_DIR
unset TEST_CODECHECKER_DIR
unset TEST_CLANG_VERSION
unset TEST_TEST_PROJECT_CONFIG
