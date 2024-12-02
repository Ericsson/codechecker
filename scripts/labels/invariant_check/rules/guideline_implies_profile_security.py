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


class GuidelineImpliesProfileSecurity(Base):
    kind = "guideline.implies_profile_security"
    description = """
Ensures that checkers with a "guideline" label corresponding to a published
security guideline (e.g., SEI-CERT) are added to the 'security' profile.
""".replace('\n', ' ')
    supports_fixes = True

    # Only the following guidelines will trigger the implication.
    interesting_guidelines: Set[str] = {"sei-cert",
                                        }

    @classmethod
    def check(cls, labels: MultipleLabels, _analyser: str, checker: str) \
            -> Tuple[bool, List[fixit.FixAction]]:
        guidelines: Set[str] = set(labels[checker].get("guideline", []))
        if not guidelines & cls.interesting_guidelines:
            return True, []

        profiles: Set[str] = set(labels[checker].get("profile", []))
        missing_profiles = {"security"} - profiles
        return not missing_profiles, \
            [fixit.AddLabelAction(f"profile:{profile}")
             for profile in missing_profiles]
