# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Describes the base interface for the generation of severity labels.
"""
from typing import Iterable, Optional, Tuple


class Base:
    kind = "abstract"

    def __init__(self, analyser: str):
        self.analyser = analyser

    def skip(self, checker: str) -> bool:
        """
        Returns ``True`` if the result for `checker` from the current generator
        should be discarded.
        """
        return False

    def generate(self) -> Iterable[Tuple[str, Optional[str]]]:
        """
        Returns a generator that can be consumed in order to obtain
        ``(checker, severity)`` pairs, one for each encountered checker.
        The exact details are analyser-specific!

        A ``None`` in the place of ``severity`` indicates that the ``checker``
        was encountered in the documentation, but no severity was generated.
        """
        return iter(())
