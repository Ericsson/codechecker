# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Describes the abstract base interface for an invariant verification.
"""
from typing import List, Tuple

from ...checker_labels import MultipleLabels
from ...fixit import FixAction


class Base:
    kind = "abstract"
    description = "(Abstract rule that always reports 'True'.)"
    supports_fixes = False

    @classmethod
    def check(cls, labels: MultipleLabels, checker: str) \
            -> Tuple[bool, List[FixAction]]:
        """
        Performs an implementation-specific routine that returns the
        "verification status" of the implemented invariant, and, optionally,
        the updated set of `labels` the `checker` must have in order to pass
        the invariant verification.
        """
        return True, []
