# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Setup python modules for the unit tests.
"""


import json
import os
import sys

# Add the generated thrift files for the unit tests.
BUILD_DIR = os.path.abspath(os.environ['BUILD_DIR'])
sys.path.append(os.path.join(BUILD_DIR, "thrift", "v6", "gen-py"))

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

sys.path.append(REPO_ROOT)
sys.path.append(os.path.join(REPO_ROOT, 'web'))
sys.path.append(os.path.join(REPO_ROOT, 'web', 'client'))
sys.path.append(os.path.join(REPO_ROOT, 'web', 'server'))

sys.path.append(os.path.join(REPO_ROOT, 'tools', 'codechecker_report_hash'))
