# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Setup module paths and environment variables for the functional tests.
"""


import os
import sys

# Add the generated thrift files for the functional tests.
BUILD_DIR = os.path.abspath(os.environ['BUILD_DIR'])

sys.path.append(os.path.join(BUILD_DIR, "thrift", "v6", "gen-py"))

# Setup the required environment variables for the tests.

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

sys.path.append(os.path.join(PKG_ROOT, 'lib', 'python3'))
