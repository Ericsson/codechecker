# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Clang Static Analyzer."""
from typing import Optional
import urllib.parse

from ... import http_ as http, transformer
from ...projects.llvm import fetch_llvm_release_versions
from ...transformer import Version
from .generic import HTMLAnchorVerifier
from .status import Status


class ClangSAVerifier(HTMLAnchorVerifier):
    """
    Verifies and allows downgrading the documentation for Clang Static Analyzer
    checkers.
    """

    kind = "clangsa"

    def __init__(self, analyser: str,
                 cache_size: int = http.CachingHTMLAcquirer.DefaultCacheSize):
        super().__init__(analyser=analyser, cache_size=cache_size)

        self._release_fixer = transformer.PerReleaseRules(
            releases=fetch_llvm_release_versions)
        # Analysis information in the Sphinx-based structure was introduced in
        # llvm/llvm-project 1a17032b788016299ea4e3c4b53670c6dcd94b4f
        # which was first present in version 9.0.0-rc1.
        self._release_fixer.add_rule(
            "https://releases.llvm.org/<VERSION>/tools/clang/docs/analyzer/"
            "checkers.html#<ANCHOR>",
            Version("9.0.0"))

        self._reset_pattern = transformer.ReplacePatternApplicator(
            "https://clang.llvm.org/docs/analyzer/checkers.html#<ANCHOR>")

    def _fake_anchor(self, checker: str) -> str:
        """
        Returns a normalised version of the checker's name which can be used
        as a fake anchor to initiate an anchor search.

        This anchor is most often never the real one, because there is not a
        one-to-one mapping from checker names to anchors, as the actual
        anchors, e.g., ``core-dividezero-c-c-objc`` (for the HTML text
        "core.DivideZero (C, C++, ObjC)") can not be generated automatically
        from the actual checker name.
        Luckily, at least as of last change to this logic, the anchors
        generated here are at least substrings of the actual anchors.
        """
        return checker.replace('.', '-').lower()

    def reset(self, checker: str, url: str) -> Optional[str]:
        _, anchor = self._http.split_anchor(url)
        if not anchor:
            anchor = self._fake_anchor(checker)
        return self._reset_pattern(anchor=anchor)

    def try_fix(self, checker: str, url: str) -> Optional[str]:
        _, anchor = self._http.split_anchor(url)
        checker_name_in_anchor = self._fake_anchor(checker)

        def _try_anchor(url: str) -> Optional[str]:
            other_anchor = next(
                (a for a in self.find_anchors_for_text(url, checker)
                 if a.startswith(checker_name_in_anchor)), None)
            if other_anchor:
                return urllib.parse.urlparse(url). \
                        _replace(fragment=other_anchor). \
                        geturl()
            return None

        attempt = _try_anchor(url)
        if attempt:
            return attempt

        for release_url in self._release_fixer.generate_urls(anchor=anchor):
            if self.verify(checker, release_url)[0] == Status.OK:
                return release_url
            attempt = _try_anchor(release_url)
            if attempt:
                return attempt
