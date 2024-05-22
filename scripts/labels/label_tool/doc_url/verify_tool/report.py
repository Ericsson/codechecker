# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the high-level reports printed to the user."""
from collections import deque
from typing import List

from ...checker_labels import SingleLabels
from ...output import log, coloured, emoji
from ...util import plural
from ..output import Settings as OutputSettings


def print_verifications(analyser: str,
                        urls: SingleLabels,
                        ok: List[str],
                        not_ok: List[str],
                        missing: List[str]):
    if missing:
        log("%s%s: %s %s %s not have a `doc_url` label!",
            emoji(":magnifying_glass_tilted_left:"
                  ":magnifying_glass_tilted_right:  "),
            analyser,
            coloured("%d" % len(missing), "yellow"),
            plural(missing, "checker", "checkers"),
            plural(missing, "does", "do"),
            )
        if OutputSettings.report_missing():
            deque((log("    %s· %s ",
                       emoji(":bookmark:  "),
                       coloured(checker, "yellow"))
                   for checker in sorted(missing)),
                  maxlen=0)

    if not not_ok:
        if ok:
            log("%s%s: All %s %s successfully verified.",
                emoji(":magnifying_glass_tilted_left::check_mark_button:  "),
                analyser,
                coloured("%d" % len(ok), "green"),
                plural(ok, "checker", "checkers"),
                )
    else:
        log("%s%s: %s %s failed documentation verification. (%s succeeded.)",
            emoji(":magnifying_glass_tilted_left::warning:  "),
            analyser,
            coloured("%d" % len(not_ok), "red"),
            plural(not_ok, "checker", "checkers"),
            coloured("%d" % len(ok), "green")
            if ok else coloured("0", "red"),
            )

    for checker in sorted((ok if OutputSettings.report_ok() else []) +
                          not_ok):
        is_ok = (checker in ok) if OutputSettings.report_ok() else False
        icon = ":globe_showing_Europe-Africa:" if is_ok \
            else ":skull_and_crossbones:  "
        colour = "green" if is_ok else "red"

        log("    %s· %s [%s]", emoji(icon), coloured(checker, colour),
            urls[checker])


def print_resets(analyser: str,
                 attempted: int,
                 new_urls: SingleLabels):
    if not attempted:
        log("%s%s: Did not attempt any resets.",
            emoji(":magnifying_glass_tilted_left:"
                  ":left_arrow_curving_right:  "),
            analyser,
            )
        return

    log("%s%s: Tried to reset %s %s documentation URL. %s changed.",
        emoji(":magnifying_glass_tilted_left::right_arrow_curving_left:  "),
        analyser,
        coloured("%d" % attempted, "magenta"),
        plural(attempted, "checker's", "checkers'"),
        coloured("%d" % len(new_urls), "cyan")
        if new_urls else coloured("0", "red"),
        )
    deque((log("    %s· %s [%s]",
               emoji(":magic_wand:  "),
               coloured(checker, "cyan"),
               new_urls[checker])
           for checker in sorted(new_urls)),
          maxlen=0)


def print_fixes(analyser: str,
                urls: SingleLabels,
                found: SingleLabels,
                gone: SingleLabels):
    if not gone:
        if found:
            log("%s%s: Found new documentation for all %s %s.",
                emoji(":magnifying_glass_tilted_left::telescope:  "),
                analyser,
                coloured("%d" % len(found), "green"),
                plural(len(found), "checker", "checkers"),
                )
    else:
        if not found:
            log("%s%s: All %s %s gone.",
                emoji(":magnifying_glass_tilted_left::headstone:  "),
                analyser,
                coloured("%d" % len(gone), "red"),
                plural(len(gone), "checker", "checkers"),
                )
        else:
            log("%s%s: %s %s gone. (Found %s.)",
                emoji(":magnifying_glass_tilted_left::bar_chart:  "),
                analyser,
                coloured("%d" % len(gone), "red"),
                plural(len(gone), "checker", "checkers"),
                coloured("%d" % len(found), "green")
                if found else coloured("0", "red")
                )

    for checker in sorted(found.keys() | gone.keys()):
        is_found = checker in found
        icon = ":globe_showing_Europe-Africa:  " if is_found \
            else ":skull_and_crossbones:  "
        colour = "green" if is_found else "red"
        url_to_print = found[checker] if is_found else gone[checker]

        log("    %s· %s [%s]", emoji(icon), coloured(checker, colour),
            url_to_print)
