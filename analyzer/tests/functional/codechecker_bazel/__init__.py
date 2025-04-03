# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import sys

# THIS TENDS TO CONTAIN analyzer/ ON THE END OF IT
REPO_ROOT = os.path.abspath(os.environ['REPO_ROOT'])
PKG_ROOT = os.path.join(REPO_ROOT, 'build', 'CodeChecker')


sys.path.append(os.path.join(PKG_ROOT, 'bin'))
