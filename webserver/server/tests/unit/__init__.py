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

import json
import os
import sys

# Add the generated thrift files for the unit tests.
sys.path.append("build/thrift/v6/gen-py/")

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

__LAYOUT_FILE_PATH = os.path.join(PKG_ROOT, 'config', 'package_layout.json')
with open(__LAYOUT_FILE_PATH) as layout_file:
    __PACKAGE_LAYOUT = json.load(layout_file)
sys.path.append(os.path.join(
    PKG_ROOT, __PACKAGE_LAYOUT['static']['gencodechecker']))

sys.path.append(REPO_ROOT)
