#!/bin/bash
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
#
# Script to run the test_stats_collect_in_headers functional test case.
#
# Usage:
#   ./scripts/test/run_stats_collect_in_headers_test.sh
#
# Note: This test requires statistics collector checkers to be available
# in your Clang Static Analyzer. The test will be skipped if checkers are
# not available.
#

set -e

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

echo "Running test_stats_collect_in_headers functional test..."
echo ""
echo "Note: If the test is skipped, it means statistics collector checkers"
echo "      are not available in your Clang Static Analyzer."
echo ""

# Run the specific test case
# Use -s to disable output capture so print statements are visible
EXTRA_PYTEST_ARGS='-k test_stats_collect_in_headers -s' \
TEST=tests/functional/statistics/test_statistics.py \
make test_web_feature
