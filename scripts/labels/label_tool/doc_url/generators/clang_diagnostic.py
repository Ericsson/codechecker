# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Clang compiler diagnostics (implemented through CodeChecker as Clang-Tidy
checks.)
"""
from typing import Iterable, Optional, Tuple

from ... import http_ as http
from .base import Base


class ClangDiagnosticGenerator(Base):
    """
    Generates documentation URLs for Clang diagnostics from the Sphinx-based
    documentation metastructure.
    """

    kind = "clang-diagnostic"

    def __init__(self, analyser: str):
        super().__init__(analyser=analyser)
        self._http = http.HTMLAcquirer()
        self.toc_url = "https://clang.llvm.org/docs/DiagnosticsReference.html"

    diagnostic_prefixes = (
        # Warnings.
        "-W",
        # Remarks.
        "-R"
    )

    def skip(self, checker: str) -> bool:
        return not checker.startswith("clang-diagnostic")

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        dom = self._http.get_dom(self.toc_url)
        if dom is None:
            return iter(())

        for section in dom.xpath(
                "//section[descendant::a[@class=\"toc-backref\"]]"):
            anchor = section.find(".//a[@class=\"headerlink\"]") \
                .attrib["href"] \
                .lstrip('#')
            header = list(section.find(".//a[@class=\"toc-backref\"]")
                          .itertext())
            diagnostic_name = header[0]
            if not diagnostic_name.startswith(self.diagnostic_prefixes):
                continue

            checker_name = diagnostic_name
            for prefix in self.diagnostic_prefixes:
                if checker_name.startswith(prefix):
                    checker_name = checker_name.replace(prefix, '', 1)
            if not checker_name:
                continue
            checker_name = f"clang-diagnostic-{checker_name}"

            yield checker_name, f"{self.toc_url}#{anchor}"
