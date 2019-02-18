# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test project helpers.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
from . import env


def path(test_project):
    return os.path.join(env.test_proj_root(), test_project)
