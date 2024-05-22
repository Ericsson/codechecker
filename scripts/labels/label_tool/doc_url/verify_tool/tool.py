# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the tool's pipeline."""
from enum import IntFlag, auto as Enumerator
from typing import NamedTuple, Optional, Tuple, Type, cast

from codechecker_common.compatibility.multiprocessing import Pool

from ...checker_labels import SingleLabels
from ...output import trace
from ...util import plural
from . import action, report


class Statistics(NamedTuple):
    """
    The result of the execution of one analyser's verification.
    """

    Analyser: str
    Checkers: int
    Verifier: str
    Skipped: Optional[int]
    Reset: Optional[int]
    Missing: Optional[int]
    Verified: Optional[int]
    OK: Optional[int]
    Not_OK: Optional[int]
    Found: Optional[int]
    Gone: Optional[int]


class ReturnFlags(IntFlag):
    """
    A bit flag structure indicating the return value of the execution of the
    tool's `execute` function.
    """
    # Zero indicates an all-success, but `Enumerator()` starts from 1.

    # Reserved flags used for other purposes external to the tool.
    GeneralError = Enumerator()
    ConfigurationOrArgsError = Enumerator()

    HadMissing = Enumerator()
    HadNotOK = Enumerator()
    HadFound = Enumerator()
    HadGone = Enumerator()


def execute(analyser: str,
            verifier_class: Type,
            labels: SingleLabels,
            process_count: int,
            skip_fixes: bool,
            reset_urls: bool
            ) -> Tuple[ReturnFlags, SingleLabels, Statistics]:
    """Runs one instance of the verification pipeline."""
    trace("Running over %d %s.",
          process_count,
          plural(process_count, "process", "processes"))
    status = cast(ReturnFlags, 0)
    stats = Statistics(Analyser=analyser,
                       Checkers=len(labels),
                       Verifier=verifier_class.kind,
                       Skipped=None,
                       Reset=None,
                       Missing=None,
                       Verified=None,
                       OK=None,
                       Not_OK=None,
                       Found=None,
                       Gone=None,
                       )

    with Pool(max_workers=process_count,
              initializer=action.Worker.factory,
              initargs=(verifier_class, analyser,)
              ) as pool:
        if reset_urls:
            attempt, new_urls = action.run_reset(pool, labels)
            report.print_resets(analyser, attempt, new_urls)
            labels.update(new_urls)
            stats = stats._replace(Reset=len(new_urls) if new_urls else None,
                                   )

        urls_to_save: SingleLabels = dict()
        ok, skip, not_ok, missing = action.run_verification(pool, labels)
        report.print_verifications(analyser, labels, ok, not_ok, missing)
        urls_to_save.update({checker: labels[checker] for checker in ok})
        verified = len(labels) - skip - len(missing)
        stats = stats._replace(Skipped=skip if skip else None,
                               Missing=len(missing) if missing else None,
                               Verified=verified if verified else None,
                               OK=len(ok) if ok else None,
                               Not_OK=len(not_ok) if not_ok else None,
                               )
        status = status | (ReturnFlags.HadMissing if missing else 0)

        if not_ok:
            status |= ReturnFlags.HadNotOK
            if not skip_fixes:
                found, gone = action.run_fixes(
                    pool, {checker: labels[checker] for checker
                           in labels.keys() & not_ok}
                )
                report.print_fixes(analyser, labels, found, gone)
                urls_to_save.update(found)
                stats = stats._replace(Found=len(found) if found else None,
                                       Gone=len(gone) if gone else None,
                                       )
                status = status | (ReturnFlags.HadFound if found else 0) \
                    | (ReturnFlags.HadGone if gone else 0)

    return status, urls_to_save, stats
