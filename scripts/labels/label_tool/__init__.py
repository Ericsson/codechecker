# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
This library ships reusable components and user-facing tools to verify,
generate, and adapt the checker labels in the CodeChecker configuration
structure.
"""
# Load the interpreter injection first.
from . import codechecker

from . import \
    checker_labels, \
    http_, \
    output, \
    projects, \
    transformer, \
    util


__all__ = [
    "checker_labels",
    "codechecker",
    "http_",
    "output",
    "projects",
    "transformer",
    "util",
]
