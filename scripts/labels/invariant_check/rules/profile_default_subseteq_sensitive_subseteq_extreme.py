# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from typing import List, Set, Tuple

from ...checker_labels import MultipleLabels
from ... import fixit
from .base import Base


class ProfileDefaultSubsetEqSensitiveSubsetEqExtreme(Base):
    kind = "profile.default_partof_sensitive_partof_extreme"
    description = """
Ensures that the 'default' profile is a subset of the 'sensitive' profile,
which is a subset of the 'extreme' profile, transitively.
""".replace('\n', ' ')
    supports_fixes = True

    @classmethod
    def check(cls, labels: MultipleLabels, _analyser: str, checker: str) \
            -> Tuple[bool, List[fixit.FixAction]]:
        profiles: Set[str] = set(labels[checker].get("profile", []))
        expected_profiles: Set[str] = set()

        if "default" in (profiles | expected_profiles):
            expected_profiles.add("sensitive")
        if "sensitive" in (profiles | expected_profiles):
            expected_profiles.add("extreme")

        missing_profiles = expected_profiles - profiles
        return not missing_profiles, \
            [fixit.AddLabelAction(f"profile:{profile}")
             for profile in missing_profiles]
