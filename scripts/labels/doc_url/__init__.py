# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Verifies and generates fixed ``doc_url`` labels for checkers in the
configuration.
"""
from . import \
    generators, \
    output, \
    verifiers


__all__ = [
    "generators",
    "output",
    "verifiers",
]
