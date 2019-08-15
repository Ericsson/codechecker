# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Setup module paths and environment variables for the unit tests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import sys

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])

sys.path.append(REPO_ROOT)