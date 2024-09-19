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


class ProfileNoAlphaCheckersInProduction(Base):
    kind = "profile.no_alpha_checkers_in_production_profiles"
    description = """
Ensures that Clang SA checkers in the 'alpha.' (and 'debug.') checker groups
do not belong to a production-grade "profile", e.g., 'default' or 'security'.
""".replace('\n', ' ')
    supports_fixes = True

    # FIXME(v6.25?): It is planned that we will create a profile specifically
    # for Alpha checkers that are not good enough to be possible to lift from
    # Alpha status, but not bad enough to be completely unusable, in order to
    # suggest ad-hoc use for interested clients.
    # These groups **SHOULD** allow Alpha checkers.
    profiles_allowing_alphas: Set[str] = {"<placeholder>",
                                          }

    @classmethod
    def supports_analyser(cls, analyser: str) -> bool:
        return analyser == "clangsa"

    @classmethod
    def check(cls, labels: MultipleLabels, analyser: str, checker: str) \
            -> Tuple[bool, List[fixit.FixAction]]:
        if not cls.supports_analyser(analyser) \
                or not checker.startswith(("alpha.", "debug.")):
            return True, []

        profiles: Set[str] = set(labels[checker].get("profile", []))
        unexpected_profiles = profiles - cls.profiles_allowing_alphas

        return not unexpected_profiles, \
            [fixit.RemoveLabelAction(f"profile:{profile}")
             for profile in unexpected_profiles]
