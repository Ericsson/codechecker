# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import sys

REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')

os.environ["CC_DATA_FILES_DIR"] = PKG_ROOT

sys.path.append(REPO_ROOT)
sys.path.append(os.path.join(
  REPO_ROOT, 'analyzer', 'tools', 'statistics_collector'))
sys.path.append(os.path.join(REPO_ROOT, 'tools', 'report-converter'))
sys.path.append(os.path.join(PKG_ROOT, 'lib', 'python3'))
