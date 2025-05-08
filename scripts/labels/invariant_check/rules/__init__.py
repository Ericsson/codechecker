# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
This package contains the implementation for individually executable invariant
verification rules.
"""
from typing import List, Type

from .base import Base
from .guideline_implies_profile_security import \
    GuidelineImpliesProfileSecurity
from .guideline_requires_rule_number_annotation import \
    GuidelineRequiresRuleNumberAnnotation
from .guideline_rule_number_annotation_requires_guideline import \
    GuidelineRuleNumberAnnotationRequiresGuideline
from .profile_default_subseteq_sensitive_subseteq_extreme \
    import ProfileDefaultSubsetEqSensitiveSubsetEqExtreme
from .profile_no_alpha_checkers_in_production import \
    ProfileNoAlphaCheckersInProduction

__all__ = [
    "Base",
    "GuidelineImpliesProfileSecurity",
    "GuidelineRequiresRuleNumberAnnotation",
    "GuidelineRuleNumberAnnotationRequiresGuideline",
    "ProfileDefaultSubsetEqSensitiveSubsetEqExtreme",
    "ProfileNoAlphaCheckersInProduction",
]

rules_visible_to_user: List[Type[Base]] = \
    [globals()[cls_name] for cls_name in sorted(__all__) if cls_name != "Base"]
