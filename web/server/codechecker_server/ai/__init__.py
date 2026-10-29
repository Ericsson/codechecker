# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
AI-assisted explanation of analysis reports.
"""

from .config import AIConfig
from .explain import PathEvent, ReportContext, explain_report
from .client import AIProviderError

__all__ = [
    'AIConfig',
    'AIProviderError',
    'PathEvent',
    'ReportContext',
    'explain_report',
]
