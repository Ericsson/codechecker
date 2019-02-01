# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Setup python modules for the unit tests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import sys

# Add the generated thrift files for the unit tests.
sys.path.append("build/thrift/v6/gen-py/")

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

sys.path.append(os.path.join(PKG_ROOT, 'lib', 'python2.7'))
