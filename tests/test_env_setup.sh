#!/usr/bin/env bash

export TEST_TESTS_DIR=$(readlink -f "$(dirname "$BASH_SOURCE")")

export TEST_CODECHECKER_PACKAGE_DIR=`mktemp -d`
export TEST_CODECHECKER_DIR="$TEST_CODECHECKER_PACKAGE_DIR/CodeChecker"
echo "Temporary directory for testing created: " $TEST_CODECHECKER_PACKAGE_DIR
export TEST_CLANG_VERSION="stable"

export TEST_TEST_PROJECT_CONFIG="$TEST_TESTS_DIR/test_projects/test_files/project_info.json"
