# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the high-level user-facing actions."""


from codechecker_common.compatibility.multiprocessing import Pool

from ...checker_labels import MultipleLabels


def verify_invariant() -> None:
    pass


def run_check(pool: Pool, labels: MultipleLabels) -> None:
    pass
