# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Miscellaneous `Exception` classes."""


class EngineError(Exception):
    """Indiciates a generic failure of a generator or verifier engine."""
    pass
