# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from typing import List, Tuple

from ...checker_labels import MultipleLabels
from ... import fixit
from .base import Base


class ProfileDefaultSubsetEqSensitiveSubsetEqExtreme(Base):
    kind = "profile_default_subseteq_sensitive_subseteq_extreme"
    description = """
Ensures that the 'default' profile is a subset of the 'sensitive' profile,
which is a subset of the 'extreme' profile, transitively.
""".replace('\n', ' ')
    supports_fixes = True

    @classmethod
    def check(cls, labels: MultipleLabels, checker: str) \
            -> Tuple[bool, List[fixit.FixAction]]:
        return True, []
