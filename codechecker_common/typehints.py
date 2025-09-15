# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Type hint (`typing`) extensions.
"""
from typing import Any, Protocol, TypeVar


_T_contra = TypeVar("_T_contra", contravariant=True)


class LTComparable(Protocol[_T_contra]):
    def __lt__(self, other: _T_contra, /) -> bool: ...


class LEComparable(Protocol[_T_contra]):
    def __le__(self, other: _T_contra, /) -> bool: ...


class GTComparable(Protocol[_T_contra]):
    def __gt__(self, other: _T_contra, /) -> bool: ...


class GEComparable(Protocol[_T_contra]):
    def __ge__(self, other: _T_contra, /) -> bool: ...


# pylint: disable=too-many-ancestors
class Orderable(LTComparable[Any], LEComparable[Any],
                GTComparable[Any], GEComparable[Any], Protocol):
    """Type hint for something that supports rich comparison operators."""
