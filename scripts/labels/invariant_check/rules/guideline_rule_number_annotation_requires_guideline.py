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


class GuidelineRuleNumberAnnotationRequiresGuideline(Base):
    kind = "guideline.rule_number_annotation_requires_guideline"
    description = """
Ensures that checkers with a "<guideline-name>:<rule-number>" labels for a
published security guideline (e.g., SEI-CERT) must be labelled with a
"guideline:<guideline-name>" label as well.
""".replace('\n', ' ')
    supports_fixes = True

    # Only the following guidelines will trigger the check.
    interesting_guidelines: Set[str] = {"sei-cert",
                                        }

    @classmethod
    def check(cls, labels: MultipleLabels, analyser: str, checker: str) \
            -> Tuple[bool, List[fixit.FixAction]]:
        labelled_guidelines: Set[str] = set(labels[checker]
                                            .get("guideline", []))
        missing_guidelines: List[str] = []

        for guideline in cls.interesting_guidelines:
            guideline_rule_annotations = set(labels[checker]
                                             .get(guideline, []))
            if guideline_rule_annotations and \
                    guideline not in labelled_guidelines:
                missing_guidelines.append(guideline)
                log("%s%s: %s/%s - \"%s\" without \"%s\"",
                    emoji(":police_car_light:  "),
                    coloured("RULE VIOLATION", "red"),
                    analyser, checker,
                    "\", \"".join((
                        coloured(f"{guideline}:{rule_annotation}", "green")
                        for rule_annotation in guideline_rule_annotations
                    )),
                    coloured(f"guideline:{guideline}", "red"),
                    )

        return not missing_guidelines, \
            [fixit.AddLabelAction(f"guideline:{guideline}")
             for guideline in missing_guidelines]
