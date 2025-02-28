# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from typing import List, Set, Tuple

from ...checker_labels import MultipleLabels
from ...output import log, coloured, emoji
from ... import fixit
from .base import Base


class GuidelineRequiresRuleNumberAnnotation(Base):
    kind = "guideline.requires_rule_number_annotation"
    description = """
Checks that checkers with a "guideline" label corresponding to a published
security guideline (e.g., SEI-CERT) must be labelled with a
"<guideline-name>:<rule-number>" label as well.
""".replace('\n', ' ')
    supports_fixes = False

    # Only the following guidelines will trigger the check.
    interesting_guidelines: Set[str] = {"sei-cert",
                                        }

    @classmethod
    def check(cls, labels: MultipleLabels, analyser: str, checker: str) \
            -> Tuple[bool, List[fixit.FixAction]]:
        guidelines: Set[str] = set(labels[checker].get("guideline", []))

        failed: List[str] = []
        for guideline in (guidelines & cls.interesting_guidelines):
            if not labels[checker].get(guideline, []):
                log("%s%s: %s/%s - \"%s\" without \"%s\"",
                    emoji(":police_car_light:  "),
                    coloured("RULE VIOLATION", "red"),
                    analyser, checker,
                    coloured(f"guideline:{guideline}", "green"),
                    coloured(f"{guideline}:<RULE-NUMBER>", "red"),
                    )
                failed.append(guideline)

        return not failed, []
