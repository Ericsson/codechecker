# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Fetch the list of Clang compiler diagnostic sections from the documentation.
"""
from typing import Iterable, Tuple

from lxml import html

from ... import http_ as http


URL = "https://clang.llvm.org/docs/DiagnosticsReference.html"
DiagnosticPrefixes = (
    "-W",  # Warnings.
    "-R",  # Remarks.
)


def get_clang_diagnostic_documentation(request: http.HTMLAcquirer) \
        -> Iterable[Tuple[str, str, html.HtmlElement]]:
    """
    Returns the diagnostic ``<section>``s from the DOM of the documentation
    `URL` page for Clang compiler warnings.
    """
    dom = request.get_dom(URL)
    if dom is None:
        return iter(())

    for section in dom.xpath(
            "//section[descendant::a[@class=\"toc-backref\"]]"):
        header = list(section.find(".//a[@class=\"toc-backref\"]")
                      .itertext())
        diagnostic_name = header[0]
        if not diagnostic_name.startswith(DiagnosticPrefixes):
            continue

        checker_name = diagnostic_name
        for prefix in DiagnosticPrefixes:
            if checker_name.startswith(prefix):
                checker_name = checker_name.replace(prefix, '', 1)
        if not checker_name:
            continue
        checker_name = f"clang-diagnostic-{checker_name.lower()}"

        yield checker_name, diagnostic_name, section
