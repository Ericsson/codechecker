# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Represents simple string transformations that appear in the context of
automatic fixes, and supports conflict-checking the set of these actions
whether they can be applied cleanly.
"""
from itertools import groupby
from typing import Dict, List, Optional, Tuple

from .util import remove_falsy_mapped


class FixAction:
    """
    Represents a singular fix action (the changing of a single label entry)
    difference.
    """

    def __init__(self, kind: str,
                 old_label: Optional[str], new_label: Optional[str]):
        self._kind = kind
        self.old = old_label
        self.new = new_label

    def __repr__(self) -> str:
        return f"FixAction('{self._kind}', " \
            f"'{self.old if self.old else 'None'}'" \
            f"'{self.new if self.new else 'None'}')"

    def __eq__(self, rhs) -> bool:
        if not isinstance(rhs, FixAction):
            return False
        return (self._kind, self.old, self.new) \
            == (rhs._kind, rhs.old, rhs.new)

    def __hash__(self):
        return hash((self._kind, self.old, self.new))

    def __lt__(self, rhs):
        if not isinstance(rhs, FixAction):
            raise TypeError("'<' not supported between instances of "
                            f"'{type(self)}' and '{type(rhs)}'")
        return (self._kind, self.old, self.new) < (rhs._kind, rhs.old, rhs.new)


class AddLabelAction(FixAction):
    """Represents inserting a new label into the label set of a checker."""

    def __init__(self, label: str):
        super().__init__('+', None, label)

    def __repr__(self) -> str:
        return f"+++ {self.new}"


class RemoveLabelAction(FixAction):
    """Represents removing a label from the label set of a checker."""

    def __init__(self, label: str):
        super().__init__('-', label, None)

    def __repr__(self) -> str:
        return f"--- {self.old}"


class ModifyLabelAction(FixAction):
    """
    Represents changing a label from one value to another.

    Only a complete change is modelled, sub-string changes would be
    too granular.
    """

    def __init__(self, old: str, new: str):
        super().__init__('~', old, new)

    def __repr__(self) -> str:
        return f"~~~ {self.old} -> {self.new}"


def filter_conflicting_fixes(fixes: List[FixAction]) \
        -> Tuple[bool, List[FixAction]]:
    """
    Checks whether a list of `fixes` are non-conflicting, that is, can be
    applied safely to any existing collection.

    Returns whether there were any conflicts, and the non-conflicting subset
    of the `FixAction`s, which might be empty.

    The following conflict cases are detected:

        * The same value is added (`AddLabelAction`) and removed
        (`RemoveLabelAction`) at the same time.
        * A `ModifyLabelAction` changes FROM a value that is also being added.
        * A `ModifyLabelAction` changes TO a value that is also being removed.
        * Multiple `ModifyLabelAction`s would change the same value TO
        different labels.

    Notably, the following cases are **NOT** errors, albeit being somewhat
    redundant:

        * Adding (`AddLabelAction`) the same label multiple times.
        * Removing (`RemoveLabelAction`) the same label multiple times.
        * Multiple `ModifyLabelAction`s (with different ``old`` value!)
        changing the values to the same ``new`` value.
    """
    conflict_free = True
    safe_fixes: List[FixAction] = list(fixes)

    all_labels = ({action.old for action in fixes} |
                  {action.new for action in fixes}) - {None}
    add_set = remove_falsy_mapped(
        {label: [action for action in fixes if action.new == label]
         for label in all_labels})
    remove_set = remove_falsy_mapped(
        {label: [action for action in fixes if action.old == label]
         for label in all_labels})

    add_and_remove = add_set.keys() & remove_set.keys()
    if add_and_remove:
        conflict_free = False
        safe_fixes = list(filter(lambda f: f.old not in add_and_remove
                                 and f.new not in add_and_remove,
                                 safe_fixes))

    for multiple_remove_of_same in filter(lambda kv: len(kv[1]) > 1,
                                          remove_set.items()):
        label, changes = multiple_remove_of_same
        grp = groupby(changes)
        if next(grp, True) and not next(grp, False):
            # All changes are operator ==-equal, just duplicates exist.
            continue

        conflict_free = False
        safe_fixes = list(filter(lambda f, _label=label:
                                 f.old != _label,
                          safe_fixes))

    return conflict_free, safe_fixes


FixMap = Dict[str, List[FixAction]]
