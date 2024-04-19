# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Selects the appropriate verification engine for the analyser configuration.
"""
from collections import defaultdict
from typing import Dict, Iterable, Tuple, Type, Union

from ...checker_labels import SingleLabels

from .generic import HTMLAnchorVerifier, HTTPStatusCodeVerifier

from .clang_diagnostic import ClangDiagnosticVerifier
from .clang_tidy import ClangTidyVerifier
from .clangsa import ClangSAVerifier


class _Generic:
    """
    Tag type that decides between the raw `HTTPStatusCodeVerifier` for direct
    links and the `HTMLAnchorVerifier` for single-page multi-section links.
    """

    @staticmethod
    def select(labels: SingleLabels) -> Type:
        return HTMLAnchorVerifier if any('#' in label
                                         for label in labels.values()
                                         if label) \
            else HTTPStatusCodeVerifier


# Set an analyser to explicit None to disable the default "generic" behaviour.
AnalyserVerifiers: Dict[str, Union[Type, Tuple[Type, ...]]] = defaultdict(
    lambda: _Generic,
    {
        "clangsa": ClangSAVerifier,
        "clang-tidy": (ClangTidyVerifier, ClangDiagnosticVerifier,),
    }
)


def select_verifier(analyser: str, labels: SingleLabels) -> Iterable[Type]:
    """
    Dispatches the `analyser` to one of the verifier classes and returns
    which class(es) should be used for the verification.
    """
    verifiers = AnalyserVerifiers[analyser]
    if not verifiers:
        return iter(())
    if not isinstance(verifiers, tuple):
        verifiers = (verifiers,)

    if verifiers[0] is _Generic:
        verifiers = (_Generic.select(labels),)
        AnalyserVerifiers[analyser] = verifiers[0]

    return iter(verifiers)
