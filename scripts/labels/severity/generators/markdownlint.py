# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Markdownlint."""
from typing import Iterable, Optional, Tuple

from ... import http_ as http
from ...exception import EngineError
from ...projects import markdownlint
from .base import Base


class MarkdownlintGenerator(Base):
    """
    Generates severities for Markdownlint rules.
    """

    kind = "markdownlint"

    def __init__(self, analyser: str):
        super().__init__(analyser=analyser)
        self._http = http.HTMLAcquirer()

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        try:
            version = markdownlint.get_markdownlint_latest_release(self._http)
        except Exception as e:
            raise EngineError(
                "Failed to obtain the Markdownlint documentation") from e

        url = "https://github.com/markdownlint/markdownlint/blob/" \
            f"{version}" \
            "/docs/RULES.md"
        for checker, _ in markdownlint.get_markdownlint_rules(self._http, url):
            yield checker, "STYLE"
