# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from enum import Enum, auto as Enumerator


class Status(Enum):
    """The outcome of an attempt at verifying a checker's documentation."""

    UNKNOWN = Enumerator()
    """The result could not be determined."""

    SKIP = Enumerator()
    """
    The verifier engine skipped verifying the checker.
    This is an internal indicator used for "multi-pass" verifications, and it
    is not normally reported to the user.
    """

    MISSING = Enumerator()
    """
    The verification could not execute because the documentation data is empty.
    """

    OK = Enumerator()
    """Successful."""

    NOT_OK = Enumerator()
    """Not successful. (Deterministic result.)"""
