# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the tool's pipeline."""
from enum import IntFlag, auto as Enumerator
from typing import Dict, List, NamedTuple, Optional, Tuple, Type, cast

from codechecker_common.compatibility.multiprocessing import Pool

from ...checker_labels import MultipleLabels
from ...fixit import FixAction, FixMap, \
    AddLabelAction, RemoveLabelAction, ModifyLabelAction
from ...output import log, trace, emoji, coloured
from ...util import plural
from ..rules import Base as RuleBase
from . import action


class Statistics(NamedTuple):
    """
    The result of the execution of one analyser's verification.
    """

    Analyser: str
    Checkers: int
    Rule: str
    OK: Optional[int]
    Not_OK: Optional[int]
    Fixed: Optional[int]


class ReturnFlags(IntFlag):
    """
    A bit flag structure indicating the return value of the execution of the
    tool's `execute` function.
    """
    # pylint: disable=invalid-name

    # Zero indicates an all-success, but `Enumerator()` starts from 1.

    # Reserved flags used for other purposes external to the tool.
    GeneralError = Enumerator()
    ConfigurationOrArgsError = Enumerator()

    HadNotOK = Enumerator()
    HadFixed = Enumerator()


def print_fixes(analyser: str, fixes: Dict[str, List[FixAction]]):
    if not fixes:
        return

    num_fixes = sum((len(fs) for fs in fixes.values()))
    log("%sFor analyser '%s', %d %s generated:",
        emoji(":magnifying_glass_tilted_left::bar_chart:  "),
        analyser,
        num_fixes,
        plural(num_fixes, "fix is", "fixes are"))

    for checker in sorted(fixes.keys()):
        checker_fixes = fixes[checker]
        if not checker_fixes:
            continue

        log("    %s· %s",
            emoji(":magnifying_glass_tilted_right:  "),
            coloured(checker, "cyan"))

        for fix in checker_fixes:
            if isinstance(fix, AddLabelAction):
                fix_str = f"+ {coloured(fix.new, 'green')}"
            elif isinstance(fix, ModifyLabelAction):
                fix_str = \
                    f"[{coloured(fix.old, 'red')}] -> " \
                    f"[{coloured(fix.new, 'green')}]"
            elif isinstance(fix, RemoveLabelAction):
                fix_str = f"- {coloured(fix.old, 'red')}"
            else:
                fix_str = coloured(str(fix), "magenta")

            log("        %s %s",
                emoji(":magic_wand:  "),
                fix_str)


def execute(analyser: str,
            rules: List[Type[RuleBase]],
            labels: MultipleLabels,
            process_count: int) -> Tuple[ReturnFlags,
                                         List[Statistics],
                                         FixMap]:
    """
    Runs one instance of the verification pipeline, all selected invariants
    for the checkers of an analyser.
    """
    trace("Running over %d %s.",
          process_count,
          plural(process_count, "process", "processes"))
    status = cast(ReturnFlags, 0)
    stats: List[Statistics] = []
    fixes: FixMap = {}

    rules = [rule for rule in rules if rule.supports_analyser(analyser)]
    with Pool(max_workers=process_count) as pool:
        ok_rules, not_ok_rules, fixing_rules, fixes = \
            action.run_check(pool, analyser, rules, labels)

        for rule in rules:
            stats.append(Statistics(Analyser=analyser,
                                    Checkers=len(labels),
                                    Rule=rule.kind,
                                    OK=ok_rules.get(rule.kind, None),
                                    Not_OK=not_ok_rules.get(rule.kind, None),
                                    Fixed=fixing_rules.get(rule.kind, None),
                                    ))

        status |= (ReturnFlags.HadNotOK if not_ok_rules else 0) \
            | (ReturnFlags.HadFixed if fixing_rules else 0)

    print_fixes(analyser, fixes)
    return status, stats, fixes
