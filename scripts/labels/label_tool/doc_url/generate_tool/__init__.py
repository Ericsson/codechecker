#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
This subpackage implements logic that is primarily user-facing, as opposed to
reusable library-like components.
"""
from . import \
    tool


__all__ = [
    "tool",
]
