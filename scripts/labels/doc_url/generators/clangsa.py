# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Clang Static Analyzer."""
from typing import Dict, Iterable, Optional, Tuple

from ... import http_ as http
from .base import Base


class ClangSAGenerator(Base):
    """
    Generates documentation URLs for Clang SA checkers from the Sphinx-based
    documentation metastructure.
    """

    kind = "clangsa"

    def __init__(self, analyser: str):
        super().__init__(analyser)
        self._http = http.HTMLAcquirer()
        self.toc_url = "https://clang.llvm.org/docs/analyzer/checkers.html"

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        dom = self._http.get_dom(self.toc_url)
        if dom is None:
            return iter(())

        sections: Dict[str, str] = {}
        for section in dom.xpath(
                "//section[descendant::a[@class=\"toc-backref\"]]"):
            anchor = section.find(".//a[@class=\"headerlink\"]") \
                .attrib["href"] \
                .lstrip('#')
            header = list(section.find(".//a[@class=\"toc-backref\"]")
                          .itertext())
            section_num, checker_name_parts = header[0], header[1].split(" ")
            checker_name = checker_name_parts[0]
            # languages = checker_name_parts[1] \
            #     .split('(')[0] \
            #     .split(')')[0] \
            #     .split(", ")

            if '.' not in checker_name:
                continue
            if sum((1 for c in section_num if c == '.')) != 4:
                continue
            sections[checker_name] = anchor

        # Some sections are for larger groups in the text, such as the list of
        # "Experimental checkers", or for the description of a group like
        # "core".
        non_checker_keys = {k for k in sections
                            if [k2 for k2 in sections
                                if k2.lower() != k.lower() and
                                k2.lower().startswith(f"{k.lower()}.")]
                            }

        for header in sorted(sections.keys() - non_checker_keys):
            yield header, f"{self.toc_url}#{sections[header]}"
        return iter(())
