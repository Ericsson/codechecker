# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the high-level user-facing actions."""
from collections import Counter
from itertools import chain, repeat
import sys
from typing import Dict, List, Tuple, Type

from codechecker_common.compatibility.multiprocessing import Pool

from ...checker_labels import KeySplitLabels, MultipleLabels
from ...output import Settings as GlobalOutputSettings, log, error, \
    coloured, emoji
from ...util import plural, remove_falsy_mapped
from ... import fixit
from ..output import Settings as OutputSettings
from ..rules import Base as RuleBase


def __unstar__verify_invariant(
    task_args: Tuple[Tuple[str, KeySplitLabels],
                     Tuple[str, List[Type[RuleBase]]]]
) -> Tuple[bool, List[fixit.FixAction], List[str], List[str], List[str]]:
    # Helper function because multiprocessing.pool does not have "starmap()",
    # and, as such, the arguments coming from the passed dict-element must be
    # expanded manually.
    return verify_invariant(*task_args[1], *task_args[0])


def verify_invariant(analyser: str,
                     rules: List[Type[RuleBase]],
                     checker: str,
                     labels: KeySplitLabels) \
        -> Tuple[bool, List[fixit.FixAction], List[str], List[str], List[str]]:
    status: bool = True
    fixes: Dict[str, List[fixit.FixAction]] = {}
    ok_rules, not_ok_rules = [], []

    for rule in rules:
        rule_status, rule_fixes = rule.check({checker: labels},
                                             analyser, checker)
        if rule_status:
            if OutputSettings.report_ok():
                log("%s%s/%s: %s %s",
                    emoji(":check_box_with_check:  "),
                    analyser, checker, rule.kind,
                    coloured("OK", "green"),
                    file=sys.stdout)
            ok_rules.append(rule.kind)
            continue

        log("%s%s/%s: %s %s",
            emoji(":cross_mark:  "),
            analyser, checker, rule.kind,
            coloured("NOT OK", "red"),
            file=sys.stdout)
        status = False
        not_ok_rules.append(rule.kind)

        if rule_fixes:
            fixes[rule.kind] = rule_fixes

    if fixes:
        all_fixes = list(*chain(fixes.values()))
        conflict_free, good_fixes = fixit.filter_conflicting_fixes(all_fixes)

        if not conflict_free:
            conflicts = sorted(set(all_fixes) - set(good_fixes))
            trace_info = ""
            if GlobalOutputSettings.trace():
                trace_info = "\nThe following %s can not be applied:\n" \
                    "    · %s" \
                    % (
                        plural(conflicts, "fix", "fixes"),
                        "\n    · ".join((str(fix) for fix in conflicts))
                    )

            error("%s%s/%s: %s%s",
                  emoji(":collision:  "),
                  analyser, checker,
                  coloured("FIX COLLISION", "red"),
                  trace_info)

            fixes = remove_falsy_mapped(
                {rule: [fix for fix in good_fixes
                        if fix in fixes.get(rule, [])]
                 for rule in fixes})

    return status, list(*chain(fixes.values())), \
        sorted(ok_rules), sorted(not_ok_rules), sorted(fixes.keys())


def run_check(pool: Pool,
              analyser: str,
              rules: List[Type[RuleBase]],
              labels: MultipleLabels) \
        -> Tuple["Counter[str]", "Counter[str]", "Counter[str]",
                 fixit.FixMap]:
    count_oks: "Counter[str]" = Counter()
    count_not_oks: "Counter[str]" = Counter()
    count_fixes: "Counter[str]" = Counter()
    fixes: fixit.FixMap = {}

    def _consume_result(checker: str,
                        status: bool,
                        fixes_to_apply: List[fixit.FixAction],
                        ok_rules: List[str],
                        not_ok_rules: List[str],
                        fix_rules: List[str]
                        ):
        count_oks.update(ok_rules)
        if not status:
            count_not_oks.update(not_ok_rules)
            count_fixes.update(fix_rules)
            fixes[checker] = sorted(set(fixes_to_apply))

    for (checker, _), \
            (status, fixes_to_apply, ok_rules, not_ok_rules, fix_rules) in \
            zip(labels.items(), pool.map(
                __unstar__verify_invariant,
                zip(labels.items(), repeat((analyser, rules))))):
        _consume_result(checker, status, fixes_to_apply,
                        ok_rules, not_ok_rules, fix_rules)

    return count_oks, count_not_oks, count_fixes, fixes
