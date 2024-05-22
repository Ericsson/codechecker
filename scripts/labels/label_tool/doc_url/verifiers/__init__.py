# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Implements the logic for generic and analyser-specific verification and
translation of documentation URLs.
"""
from .analyser_selection import select_verifier
from .generic import Outcome, \
    HTTPStatusCodeVerifier, HTMLAnchorVerifier
from .status import Status


__all__ = [
    "select_verifier",
    "Outcome",
    "HTTPStatusCodeVerifier",
    "HTMLAnchorVerifier",
    "Status",
]
