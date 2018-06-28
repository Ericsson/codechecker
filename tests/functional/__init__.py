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
import json

# Setup the required environment variables for the tests.

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])

# Add the generated python modules (by thrift) to the PYTHONPATH, needed
# by the tests.
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

__LAYOUT_FILE_PATH = os.path.join(PKG_ROOT, 'config', 'package_layout.json')
with open(__LAYOUT_FILE_PATH) as layout_file:
    __PACKAGE_LAYOUT = json.load(layout_file)
sys.path.append(os.path.join(
    PKG_ROOT, __PACKAGE_LAYOUT['static']['gencodechecker']))
