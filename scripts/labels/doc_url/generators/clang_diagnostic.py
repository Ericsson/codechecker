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
from ...projects.llvm import clang_diagnostic
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

    def skip(self, checker: str) -> bool:
        return not checker.startswith("clang-diagnostic")

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        for checker, _, section in clang_diagnostic \
                .get_clang_diagnostic_documentation(self._http):
            anchor = section.find(".//a[@class=\"headerlink\"]") \
                .attrib["href"] \
                .lstrip('#')

            yield checker, f"{clang_diagnostic.URL}#{anchor}"
