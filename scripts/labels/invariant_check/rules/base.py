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
    def supports_analyser(cls, _analyser: str) -> bool:
        """
        Returns whether the current guideline is applicable to checkers of
        `analyser`.
        """
        return True

    @classmethod
    def check(cls, _labels: MultipleLabels, _analyser: str, _checker: str) \
            -> Tuple[bool, List[FixAction]]:
        """
        Performs an implementation-specific routine that returns the
        "verification status" of the implemented invariant, and, optionally,
        the updated set of `labels` the `checker` must have in order to pass
        the invariant verification.
        """
        return True, []
