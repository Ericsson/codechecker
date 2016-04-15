#!/usr/bin/env bash

export TEST_TESTS_DIR=$(readlink -f "$(dirname "$BASH_SOURCE")")

export TEST_CODECHECKER_PACKAGE_DIR="$TEST_TESTS_DIR/tmp"
export TEST_CODECHECKER_DIR="$TEST_CODECHECKER_PACKAGE_DIR/CodeChecker"
export TEST_CLANG_VERSION="stable"
export TEST_DBPORT="5432"
export TEST_DBUSERNAME="postgres"
