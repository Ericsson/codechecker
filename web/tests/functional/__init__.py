# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Setup module paths and environment variables for the functional tests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import sys

# Setup the required environment variables for the tests.

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')
LIB_DIR = os.path.join(PKG_ROOT, 'lib', 'python2.7')

# Add libraries for the functional tests.
sys.path.append(LIB_DIR)

# Add the generated thrift files for the functional tests.
sys.path.append(os.path.join(LIB_DIR, 'codechecker_api_v6'))
