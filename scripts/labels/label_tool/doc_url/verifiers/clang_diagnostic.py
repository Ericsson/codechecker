# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Clang compiler diagnostics (implemented through CodeChecker as Clang-Tidy
checks).
"""
from typing import Collection, Optional, Tuple
import urllib.parse

from ... import http_ as http, transformer
from ...transformer import Version
from .generic import HTMLAnchorVerifier
from .llvm import fetch_llvm_release_versions
from .status import Status


class ClangDiagnosticVerifier(HTMLAnchorVerifier):
    """
    Verifies the documentation for Clang warnings (diagnostics).
    """

    kind = "clang-diagnostic"

    def __init__(self, analyser: str,
                 cache_size: int = http.CachingHTMLAcquirer.DefaultCacheSize):
        super().__init__(analyser=analyser, cache_size=cache_size)

        self._release_fixer = transformer.PerReleaseRules(
            releases=fetch_llvm_release_versions)
        # Clang Diagnostic reference in the Sphinx-based structure was
        # introduced in
        # llvm/llvm-project b6a3b4ba61383774dae692efb5767ffdb23ac36e
        # which was first present in version 4.0.0-rc1.
        self._release_fixer.add_rule(
            "https://releases.llvm.org/<VERSION>/tools/clang/docs/"
            "DiagnosticsReference.html#<ANCHOR>",
            Version("4.0.0"))

        self._reset_pattern = transformer.ReplacePatternApplicator(
            "https://clang.llvm.org/docs/DiagnosticsReference.html#<ANCHOR>")

    def skip(self, checker: str, url: str) -> Status:
        if not checker.startswith("clang-diagnostic"):
            # This class only verifies the clang-diagnostic- "Tidy" "checkers".
            return Status.SKIP
        if checker == "clang-diagnostic-error":
            # This is a special case of "-Werror" as parsed by CodeChecker and
            # it is not a real diagnostic that exists in the reference.
            return Status.SKIP
        if not url:
            return Status.MISSING
        return Status.OK

    def _normalise_checker_name(self, checker: str) -> Tuple[str, str]:
        """
        Returns a ``(checker_name, checker_anchor)`` after applying the usual
        naming pattern, normalising from ``clang-diagnostic-foo`` to ``-Wfoo``.
        """
        name = checker \
            .replace("clang-diagnostic-", '')
        anchor = checker \
            .replace("clang-diagnostic-", '') \
            .replace('#', '-') \
            .replace('=', '-') \
            .replace("++", '-') \
            .lower()
        return name, anchor

    def reset(self, checker: str, url: str) -> Optional[str]:
        _, anchor = self._http.split_anchor(url)
        if not anchor:
            _, anchor = self._normalise_checker_name(checker)
        return self._reset_pattern(anchor=anchor)

    anchor_prefixes = (
        # Warnings.
        ("-W", "w"),
        # Remarks.
        ("-R", "r")
    )

    def try_fix(self, checker: str, url: str) -> Optional[str]:
        _, anchor = self._http.split_anchor(url)
        normal_name, normal_anchor = self._normalise_checker_name(checker)

        def _try_anchor(prefixes: Collection[Tuple[str, str]],
                        url: str) -> Optional[str]:
            for prefix in prefixes:
                other_anchor = next(
                    (a for a
                     in self.find_anchors_for_text(
                         url, prefix[0] + normal_name)
                     if a.startswith(prefix[1] + normal_anchor)),
                    None)
                if other_anchor:
                    return urllib.parse.urlparse(url). \
                            _replace(fragment=other_anchor). \
                            geturl()
            return None

        attempt = _try_anchor(self.anchor_prefixes, url)
        if attempt:
            return attempt

        for release_url in self._release_fixer.generate_urls(anchor=anchor):
            if self.verify(checker, release_url)[0] == Status.OK:
                return release_url
            attempt = _try_anchor(self.anchor_prefixes, release_url)
            if attempt:
                return attempt
