#!/usr/bin/env bash

export TEST_CODECHECKER_PACKAGE_DIR="$(dirname "$BASH_SOURCE")/codechecker_package"
export TEST_CODECHECKER_DIR="$TEST_CODECHECKER_PACKAGE_DIR/CodeChecker"
export TEST_CLANG_VERSION="stable"
export TEST_DBPORT="5432"
export TEST_DBUSERNAME="postgres"
