# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Cppcheck."""
from collections import defaultdict
import subprocess
import sys
from typing import Iterable, Optional, Tuple

import lxml.etree

from ...exception import EngineError
from ...output import Settings as GlobalOutputSettings, trace
from .base import Base


class CppcheckGenerator(Base):
    """
    Generates severities for Cppcheck checkers based on the classification
    emitted by a ``cppcheck`` program.
    """

    kind = "cppcheck"

    def __init__(self, analyser: str):
        super().__init__(analyser=analyser)
        self._cppcheck_xml: Optional[lxml.etree.ElementTree] = None

    def fetch_cppcheck_errorlist(self) -> lxml.etree.ElementTree:
        if self._cppcheck_xml is not None:
            return self._cppcheck_xml

        try:
            stdout = subprocess.check_output(["cppcheck", "--errorlist"])
        except OSError as e:
            raise EngineError("Could not call Cppcheck, is it in 'PATH'?") \
                from e

        try:
            self._cppcheck_xml = lxml.etree.fromstring(stdout)
        except lxml.etree.LxmlError as e:
            if GlobalOutputSettings.trace():
                print("------------------------------------------------------",
                      file=sys.stderr)
                print(stdout, file=sys.stderr)
                print("------------------------------------------------------",
                      file=sys.stderr)
            raise EngineError("Could not understand the output of Cppcheck") \
                from e

        return self._cppcheck_xml

    SeverityMap = defaultdict(
        lambda: "UNSPECIFIED",
        {
            # When code is executed there is either undefined behaviour, or
            # other error, such as a memory leak, or a resource leak.
            "error": "HIGH",

            # Configuration problems.
            "information": "LOW",

            # Run-time performance suggestions based on common knowledge.
            "performance": "LOW",

            # Portability warnings, implementation-defined behaviour.
            "portability": "LOW",

            # Stylistic issues, such as unused functions, redundant code.
            "style": "STYLE",

            # When code is executed there might be undefined behaviour.
            "warning": "MEDIUM",
        }
    )

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        xml_results = self.fetch_cppcheck_errorlist()
        version = xml_results.find("./cppcheck").get("version")
        trace("Cppcheck version '%s'", version)

        for error_node in xml_results.findall("./errors/error"):
            yield "cppcheck-" + error_node.get("id"), \
                self.SeverityMap[error_node.get("severity")]
