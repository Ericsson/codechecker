# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the high-level user-facing actions."""
import sys
from typing import List, Optional, Tuple, Type

from codechecker_common.compatibility.multiprocessing import Pool

from ...checker_labels import SingleLabels
from ...output import Settings as GlobalOutputSettings, log, emoji, coloured
from ...util import _Singleton
from ..output import Settings as OutputSettings
from ..verifiers import HTTPStatusCodeVerifier, Status


class Worker(_Singleton):
    """Implementation of methods executed in a parallel computation context."""

    def __init__(self):
        """Returns the instance that was loaded as a `Singleton`."""
        if "_verifier" not in self.__dict__:
            self._verifier = None

    @staticmethod
    def factory(verifier_class: Type, analyser: str):
        """Initialises the `Singleton` with the required constructor args."""
        obj = Worker()
        obj._verifier = verifier_class(analyser)  # type: ignore
        return obj

    @property
    def verifier(self):
        return self._verifier

    @staticmethod
    def verify(task):
        """Executes the worker implementation."""
        verifier = Worker().verifier  # type: ignore
        return verify_checker(verifier, *task)

    @staticmethod
    def reset(task):
        """Executes the worker implementation."""
        verifier = Worker().verifier  # type: ignore
        return reset_checker(verifier, *task)

    @staticmethod
    def try_fix(task):
        """Executes the worker implementation."""
        verifier = Worker().verifier  # type: ignore
        return try_fix_checker(verifier, *task)


def verify_checker(verifier: HTTPStatusCodeVerifier,
                   checker: str, url: str) -> Status:
    """
    Executes the verification that `checker` has a valid, accessible
    documentation `doc_url` set.
    """
    analyser = verifier.analyser
    status = verifier.skip(checker, url)
    if status == Status.MISSING:
        if OutputSettings.report_missing():
            log("%s%s/%s: %s []",
                emoji(":white_question_mark:  "),
                analyser, checker,
                coloured("MISSING", "yellow"),
                file=sys.stdout)
        return status
    if status == Status.SKIP:
        if GlobalOutputSettings.trace():
            log("%s%s/%s: %s [%s]",
                emoji(":screwdriver:  "),
                analyser, checker,
                coloured("SKIP", "light_magenta"),
                url,
                file=sys.stderr)
        return status

    status, _ = verifier.verify(checker, url)
    if status == Status.OK:
        if OutputSettings.report_ok():
            log("%s%s/%s: %s [%s]",
                emoji(":check_box_with_check:  "),
                analyser, checker,
                coloured("OK", "green"),
                url,
                file=sys.stdout)
    elif status == Status.NOT_OK:
        log("%s%s/%s: %s [%s]",
            emoji(":cross_mark:  "),
            analyser, checker,
            coloured("NOT OK", "red"),
            url,
            file=sys.stdout)
    return status


def run_verification(pool: Pool, urls: SingleLabels) \
        -> Tuple[List[str], int, List[str], List[str]]:
    ok: List[str] = []
    skip = 0
    not_ok: List[str] = []
    missing: List[str] = []

    def _consume_result(checker: str,  s: Status):
        if s == Status.OK:
            ok.append(checker)
        elif s == Status.SKIP:
            nonlocal skip
            skip += 1
        elif s == Status.NOT_OK:
            not_ok.append(checker)
        elif s == Status.MISSING:
            missing.append(checker)

    for (checker, _), verified in zip(
            urls.items(), pool.map(Worker.verify, urls.items())):
        _consume_result(checker, verified)

    return ok, skip, not_ok, missing


def reset_checker(verifier: HTTPStatusCodeVerifier,
                  checker: str, url: str) -> Tuple[bool, Optional[str]]:
    analyser = verifier.analyser
    status = verifier.skip(checker, url)
    if status == Status.SKIP:
        return False, None

    after_reset = verifier.reset(checker, url)
    if not after_reset or after_reset == url:
        return True, None

    if GlobalOutputSettings.trace():
        log("%s%s/%s: %s [%s] -> [%s]",
            emoji(":right_arrow_curving_left:  "),
            analyser, checker,
            coloured("RESET", "cyan"),
            url, after_reset,
            file=sys.stdout)
    return True, after_reset


def run_reset(pool: Pool, urls: SingleLabels) -> Tuple[int, SingleLabels]:
    attempted = 0
    new_urls: SingleLabels = {}

    def _consume_result(checker: str,
                        was_attempted: bool,
                        new_url: Optional[str]):
        if was_attempted:
            nonlocal attempted
            attempted += 1
        if new_url:
            new_urls[checker] = new_url

    for (checker, _), (was_attempted, new_url) in zip(
            urls.items(), pool.map(Worker.reset, urls.items())):
        _consume_result(checker, was_attempted, new_url)

    return attempted, new_urls


def try_fix_checker(verifier: HTTPStatusCodeVerifier,
                    checker: str, url: str) -> Optional[str]:
    analyser = verifier.analyser
    status = verifier.skip(checker, url)
    if status == Status.SKIP:
        return None

    maybe_fixed = verifier.try_fix(checker, url)
    if not maybe_fixed:
        log("%s%s/%s: %s [%s]",
            emoji(":ghost:  "),
            analyser, checker,
            coloured("PERMANENTLY GONE", "red"),
            url,
            file=sys.stdout)
    else:
        log("%s%s/%s: %s [%s] -> [%s]",
            emoji(":sparkles:  "),
            analyser, checker,
            coloured("FOUND", "green"),
            coloured(url, "red"),
            coloured(maybe_fixed, "green"),
            file=sys.stdout)
    return maybe_fixed


def run_fixes(pool: Pool, urls: SingleLabels) -> Tuple[SingleLabels,
                                                       SingleLabels]:
    found: SingleLabels = {}
    gone: SingleLabels = {}

    def _consume_result(checker: str,
                        old_url: Optional[str],
                        new_url: Optional[str]):
        if new_url:
            found[checker] = new_url
        else:
            gone[checker] = old_url

    for (checker, old_url), new_url in zip(
            urls.items(), pool.map(Worker.try_fix, urls.items())):
        _consume_result(checker, old_url, new_url)

    return found, gone
