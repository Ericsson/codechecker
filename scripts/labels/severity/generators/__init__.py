# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Implements the logic for analyser-specific generation of severities.
"""
from .analyser_selection import select_generator
from .base import Base


__all__ = [
    "select_generator",
    "Base",
]
