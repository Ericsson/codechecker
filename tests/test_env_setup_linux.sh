#!/usr/bin/env bash

if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then export TEST_TESTS_DIR=$(greadlink -f "$(dirname "$BASH_SOURCE")")  fi
if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then export TEST_TESTS_DIR=$(readlink -f "$(dirname "$BASH_SOURCE")") fi

export TEST_CODECHECKER_PACKAGE_DIR=`mktemp -d`
export TEST_CODECHECKER_DIR="$TEST_CODECHECKER_PACKAGE_DIR/CodeChecker"
export TEST_CLANG_VERSION="stable"

export TEST_TEST_PROJECT_CONFIG="$TEST_TESTS_DIR/test_projects/test_files/project_info.json"

echo $TEST_TESTS_DIR
echo $TEST_CODECHECKER_PACKAGE_DIR
echo $TEST_CODECHECKER_DIR
echo $TEST_CLANG_VERSION
echo $TEST_TEST_PROJECT_CONFIG