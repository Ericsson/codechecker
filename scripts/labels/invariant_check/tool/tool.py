# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the tool's pipeline."""
from enum import IntFlag, auto as Enumerator
from typing import List, NamedTuple, Optional, Tuple, Type, cast

from codechecker_common.compatibility.multiprocessing import Pool

from ...checker_labels import MultipleLabels
from ...output import trace
from ...util import plural
from ..rules import Base as RuleBase
from . import action#, report


class Statistics(NamedTuple):
    """
    The result of the execution of one analyser's verification.
    """

    Analyser: str
    Checkers: int
    Invariant: str
    OK: Optional[int]
    Not_OK: Optional[int]
    Fixed: Optional[int]


class ReturnFlags(IntFlag):
    """
    A bit flag structure indicating the return value of the execution of the
    tool's `execute` function.
    """
    # Zero indicates an all-success, but `Enumerator()` starts from 1.

    # Reserved flags used for other purposes external to the tool.
    GeneralError = Enumerator()
    ConfigurationOrArgsError = Enumerator()

    HadNotOK = Enumerator()
    HadFixed = Enumerator()

def execute(analyser: str,
            rules: List[RuleBase],
            labels: MultipleLabels,
            process_count: int) -> Tuple[List[Statistics]]:
    """
    Runs one instance of the verification pipeline, all selected invariants
    for the checkers of an analyser.
    """
    trace("Running over %d %s.",
          process_count,
          plural(process_count, "process", "processes"))
    status = cast(ReturnFlags, 0)
    stats: List[Statistics] = list()

    with Pool(max_workers=process_count,
              ) as pool:
        import time
        time.sleep(60)

    return stats,

#     with Pool(max_workers=process_count,
#               initializer=action.Worker.factory,
#               initargs=(verifier_class, analyser,)
#               ) as pool:
#
#         urls_to_save: SingleLabels = dict()
#         ok, skip, not_ok, missing = action.run_verification(pool, labels)
#         report.print_verifications(analyser, labels, ok, not_ok, missing)
#         urls_to_save.update({checker: labels[checker] for checker in ok})
#         verified = len(labels) - skip - len(missing)
#         stats = stats._replace(Verifier_Skipped=skip if skip else None,
#                                Missing=len(missing) if missing else None,
#                                Verified=verified if verified else None,
#                                OK=len(ok) if ok else None,
#                                Not_OK=len(not_ok) if not_ok else None,
#                                )
#         status |= (ReturnFlags.HadMissing if missing else 0)
#
#         if not_ok:
#             status |= ReturnFlags.HadNotOK
#             if not skip_fixes:
#                 found, gone = action.run_fixes(
#                     pool, {checker: labels[checker] for checker
#                            in labels.keys() & not_ok}
#                 )
#                 report.print_fixes(analyser, found, gone)
#                 urls_to_save.update(found)
#                 stats = stats._replace(Found=len(found) if found else None,
#                                        Gone=len(gone) if gone else None,
#                                        )
#                 status |= (ReturnFlags.HadFound if found else 0) \
#                     | (ReturnFlags.HadGone if gone else 0)
#
#     return status, urls_to_save, stats
#
