# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Selects the appropriate generator engine for the analyser configuration.
"""
from typing import Dict, Iterable, Tuple, Type, Union

from .clang_diagnostic import ClangDiagnosticGenerator
from .cppcheck import CppcheckGenerator
from .pylint import PylintGenerator


AnalyserGenerators: Dict[str, Union[Type, Tuple[Type, ...]]] = {
    "clang-tidy": (ClangDiagnosticGenerator,),
    "cppcheck": CppcheckGenerator,
    "pylint": PylintGenerator,
}


def select_generator(analyser: str) -> Iterable[Type]:
    """
    Dispatches the `analyser` to one of the generator classes and returns
    which class(es) should be used for the label generation.
    """
    generators = AnalyserGenerators.get(analyser)
    if not generators:
        return iter(())
    if not isinstance(generators, tuple):
        generators = (generators,)
        AnalyserGenerators[analyser] = generators[0]

    return iter(generators)
