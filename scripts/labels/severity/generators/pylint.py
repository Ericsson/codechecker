# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""PyLint."""
from collections import defaultdict
import re
import subprocess
from typing import Iterable, Optional, Tuple

from ...exception import EngineError
from ...output import trace
from .base import Base


class PylintGenerator(Base):
    """
    Generates severities for PyLint checkers based on the classification
    emitted by a ``pylint`` program.
    """

    kind = "pylint"

    def __init__(self, analyser: str):
        super().__init__(analyser=analyser)
        self._pylint_msgs: Optional[str] = None

    def fetch_pylint_msgs(self) -> str:
        if self._pylint_msgs is not None:
            return self._pylint_msgs

        try:
            version = subprocess.check_output(["pylint", "--version"])
            trace("pylint version '%s'",
                  version.decode().split('\n')[0].split(' ')[1])
            self._pylint_msgs = subprocess.check_output(
                ["pylint", "--list-msgs"]) \
                .decode()
        except OSError as e:
            raise EngineError("Could not call pylint, is it in 'PATH'?") \
                from e

        return self._pylint_msgs

    SeverityMap = defaultdict(
        lambda: "UNSPECIFIED",
        {
            # Fatal: An error occurred which prevented pylint from doing
            # further processing.
            'F': "CRITICAL",

            # Error: Probable bugs in the code.
            'E': "HIGH",

            # Warning: Python-specific problems.
            'W': "MEDIUM",

            # Refactor: Bad code smell.
            'R': "STYLE",

            # Convention: Programming standard violation.
            'C': "LOW",
        }
    )

    pattern = re.compile(r"^:(?P<name>[^ ]+) \((?P<kind>\S)(?P<id>\S+)\): .*")

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        msgs = self.fetch_pylint_msgs()
        for line in msgs.split('\n'):
            match = self.pattern.match(line)
            if not match:
                continue

            yield match.group("name"), self.SeverityMap[match.group("kind")]
