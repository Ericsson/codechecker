# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Helper package to hoist common logic specific to the LLVM Project."""
from . import \
    clang_diagnostic
from .releases import fetch_llvm_release_versions


__all__ = [
    "clang_diagnostic",
    "fetch_llvm_release_versions",
]
