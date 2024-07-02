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
from typing import Optional, Tuple


class FixAction:
    """
    Represents a singular fix action (the changing of a single label entry)
    difference.
    """

    def __init__(self, kind: str,
                 old_label: Optional[str], new_label: Optional[str]):
        self.kind = kind
        self.old = old_label
        self.new = new_label

    def __repr__(self) -> str:
        return "FixAction" \
            '(' \
            f"'{self.kind}', " \
            f"{'%s'.format(self.old) if self.old else 'None'}, " \
            f"{'%s'.format(self.new) if self.old else 'None'}" \
            ')'


class AddLabelAction(FixAction):
    """Represents inserting a new label into the label set of a checker."""

    def __init__(self, label: str):
        super().__init__('+', None, label)

    def __repr__(self) -> str:
        return f"+++ {self.new}"


class DeleteLabelAction(FixAction):
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
