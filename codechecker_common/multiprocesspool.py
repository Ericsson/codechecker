# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Multiprocess compatibility module.
"""

import sys

# pylint: disable=unused-import
if sys.platform in ["darwin", "win32"]:
    from multiprocess import Pool as MultiProcessPool
else:
    from concurrent.futures import ProcessPoolExecutor as MultiProcessPool
