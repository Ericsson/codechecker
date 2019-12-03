# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Setup python modules for the unit tests.
"""


import os
import sys

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

sys.path.append(REPO_ROOT)
sys.path.append(os.path.join(REPO_ROOT, 'tools', 'codechecker_report_hash'))
sys.path.append(os.path.join(REPO_ROOT, 'analyzer', 'tools',
                             'statistics_collector'))
