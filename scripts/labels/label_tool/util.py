# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Helper functions, mixin classes, and miscellaneous utilities."""
import bisect
from typing import Any, Callable, Collection, Dict, List, Optional, \
    Sequence, Type, TypeVar, Union


_T = TypeVar("_T")

Ternary = Optional[bool]


class _Singleton:
    """
    Helper class to implement the global Singleton pattern.

    This helper is needed because multiprocessed executions need to spawn a
    globally available state such that `.map()` on the executor can work
    without having to serialise a complex state object over the communication
    channel between the manager and the processes.
    """
    _instances: Dict[Type, Any] = dict()

    def __new__(cls, *args, **kwargs) -> object:
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__new__(cls)
            cls._instances[cls].__init__(*args, **kwargs)
        return cls._instances[cls]


def plural(c: Union[int, Collection], s: str, p: str) -> str:
    if not isinstance(c, int):
        c = len(c)
    return s if c == 1 else p


def find_if(s: Sequence[_T], p: Callable[[_T], bool]) -> Optional[int]:
    """
    Returns the index of the first element in the list `s` which satisfies the
    given predicate `p`, or `None` if no such element exists.
    """
    return next((i for i, e in enumerate(s) if p(e)), None)


def lower_bound(l_: List[_T], e: _T) -> Optional[_T]:
    """
    Searches for the first element in the list `l_` which is **not** ordered
    before (using ``<``) `e`, i.e., an ``x`` that is ``max(x)`` such that
    ``x <= e``.

    `l_` must be sorted and must not contain duplicates.

    If no such element is found (`l_` is empty, or `e` is either ``<`` or ``>``
    than **all** elements of `l_`), returns `None`.
    """
    if not l_:
        return None

    idx = bisect.bisect_left(l_, e)  # type: ignore
    if idx == len(l_):
        # e > all elements of l, no element is <=.
        return None
    if idx == 0:
        # e <= all elements of l.
        if l_[0] == e:
            return l_[0]

        # e < all elements of l.
        return None

    # l[idx - 1] < l[idx] <= e < l[idx + 1]
    if l_[idx] == e:
        return l_[idx]
    return l_[idx - 1]
