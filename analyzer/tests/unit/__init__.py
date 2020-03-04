# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Setup python modules for the unit tests.
"""


import os
import sys

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

sys.path.append(REPO_ROOT)
