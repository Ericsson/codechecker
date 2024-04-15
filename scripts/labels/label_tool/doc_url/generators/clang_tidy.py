# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Clang-Tidy."""
from typing import Iterable, Optional, Tuple

from ... import http_ as http
from .base import Base


class ClangTidyGenerator(Base):
    """
    Generates documentation URLs for Clang-Tidy checkers from the Sphinx-based
    documentation table of contents.
    """

    kind = "clang-tidy"

    def __init__(self, analyser: str):
        super().__init__(analyser=analyser)
        self._http = http.HTMLAcquirer()
        self.documentation_root = \
            "https://clang.llvm.org/extra/clang-tidy/checks"
        self.toc_url = f"{self.documentation_root}/list.html"

    def skip(self, checker: str) -> bool:
        return checker.startswith("clang-diagnostic") \
            or checker.startswith("clang-analyzer")

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        dom = self._http.get_dom(self.toc_url)
        if dom is None:
            return iter(())

        for link in dom.xpath("//a[contains(@class, \"reference\") and "
                              "descendant::span[@class=\"doc\"]]"):
            checker = link.text_content()
            url = link.attrib["href"]
            if self.skip(checker):
                continue

            yield checker, f"{self.documentation_root}/{url}"
