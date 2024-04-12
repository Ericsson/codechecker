# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Clang-Tidy."""
from typing import Optional

from ... import transformer
from ...transformer import Version
from .generic import HTTPStatusCodeVerifier
from .llvm import fetch_llvm_release_versions
from .status import Status


class ClangTidyVerifier(HTTPStatusCodeVerifier):
    """
    Verifies and allows downgrading the documentation for Clang-Tidy checks.
    """

    kind = "clang-tidy"

    def __init__(self, analyser: str):
        super().__init__(analyser=analyser)

        self._release_fixer = transformer.PerReleaseRules(
            releases=fetch_llvm_release_versions)
        # Clang-Tidy documentation pages in the Sphinx-based structure were
        # introduced in
        # llvm/llvm-project aabfadef84cdcc6aef529348a287e0130f7aee6d
        # which was first present in version 3.8.0-rc1.
        # Manually checking the deployment, however, shows that the links only
        # work 3.9 onwards.
        self._release_fixer.add_rule(
            "https://releases.llvm.org/<VERSION>/tools/clang/tools/extra/"
            "docs/clang-tidy/checks/<GROUP>-<NAME>.html",
            Version("3.9.0"))
        # llvm/llvm-project 6e566bc5523f743bc34a7e26f050f1f2b4d699a8
        # changed the directory structure and introduced an explicit parent
        # directory for the check's "group".
        self._release_fixer.add_rule(
            "https://releases.llvm.org/<VERSION>/tools/clang/tools/extra/"
            "docs/clang-tidy/checks/<GROUP>/<NAME>.html",
            Version("15.0.0"))

        self._reset_pattern = transformer.ReplacePatternApplicator(
            "https://clang.llvm.org/extra/clang-tidy/checks/"
            "<GROUP>/<NAME>.html")

    def skip(self, checker: str, url: str) -> Status:
        if checker.startswith("clang-diagnostic"):
            # Clang diagnostics are special, as they appear as-if they were
            # Clang-Tidy checks, but their documentation is in a completely
            # different structure.
            return Status.SKIP
        if not url:
            return Status.MISSING
        return Status.OK

    def reset(self, checker: str, url: str) -> Optional[str]:
        group, check = checker.split("-", 1)
        return self._reset_pattern(group=group, name=check)

    def try_fix(self, checker: str, url: str) -> Optional[str]:
        group, check = checker.split("-", 1)
        older_release_url = self._release_fixer(
            lambda url_: self.verify(checker, url_)[0] == Status.OK,
            group=group,
            name=check)
        if older_release_url:
            return older_release_url
