# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Verifies that the label configuration files adhere to some crucial invariants
that are required for the proper operation of the project but usually only have
been upheld as a gentlemen's agreement, without tooling.

This package implements several separate invariant rules that can be verified
and, if possible as such, fixed automatically.
"""
from . import \
    output, \
    rules


__all__ = [
    "output",
    "rules",
]
