# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides implementations for the tool's pipeline."""
from collections import deque
from enum import IntFlag, auto as Enumerator
import sys
from typing import List, NamedTuple, Optional, Set, Tuple, Type, cast

from ...checker_labels import SingleLabels
from ...output import Settings as GlobalOutputSettings, log, coloured, emoji
from ...util import plural
from ..generators.base import Base
from ..output import Settings as OutputSettings


class Statistics(NamedTuple):
    """
    The result of the execution of one generator.
    """

    Analyser: str
    Generator: str
    Checkers: int
    Generator_Skipped: Optional[int]
    Directive_Skipped: Optional[int]
    Missing: Optional[int]
    OK: Optional[int]
    Updated: Optional[int]
    Gone: Optional[int]
    New: Optional[int]
    All_Changed: int
    Not_Found: Optional[int]


class ReturnFlags(IntFlag):
    """
    A bit flag structure indicating the return value of the tool's `execute`
    function.
    """
    # pylint: disable=invalid-name

    # Zero indicates an all-success, but `Enumerator()` starts from 1.

    # Reserved flags used for other purposes external to the tool.
    GeneralError = Enumerator()
    ConfigurationOrArgsError = Enumerator()

    HadUpdate = Enumerator()
    HadNew = Enumerator()
    HadGone = Enumerator()
    RemainsMissing = Enumerator()


def run_generator(generator: Base, urls: SingleLabels,
                  checkers_to_skip: Set[str]) \
        -> Tuple[List[str], SingleLabels, SingleLabels, List[str],
                 List[str], List[str]]:
    analyser = generator.analyser
    ok: List[str] = []
    updated: SingleLabels = {}
    new: SingleLabels = {}
    gone: List[str] = []
    generator_skip: List[str] = []
    directive_skip: List[str] = []

    generation_result: SingleLabels = dict(generator.generate())
    for checker in sorted(urls.keys() | generation_result.keys()):
        if generator.skip(checker):
            if GlobalOutputSettings.trace():
                log("%s%s/%s: %s",
                    emoji(":screwdriver:  "),
                    analyser, checker,
                    coloured("SKIP", "light_magenta"),
                    file=sys.stderr)
            generator_skip.append(checker)
            continue
        if checker in checkers_to_skip:
            if GlobalOutputSettings.trace():
                log("%s%s/%s: %s",
                    emoji(":stop_sign:  "),
                    analyser, checker,
                    coloured("DIRECTIVE-SKIP", "light_magenta"),
                    file=sys.stderr)
            directive_skip.append(checker)
            continue

        existing_url, new_url = \
            urls.get(checker), generation_result.get(checker)

        if not existing_url:
            if new_url:
                new[checker] = new_url
                log("%s%s/%s: %s [%s]",
                    emoji(":magic_wand:  "),
                    analyser, checker,
                    coloured("NEW", "magenta"),
                    new_url,
                    file=sys.stdout)
            else:
                if OutputSettings.report_missing():
                    log("%s%s/%s: %s []",
                        emoji(":white_question_mark:  "),
                        analyser, checker,
                        coloured("MISSING", "yellow"),
                        file=sys.stdout)
        elif existing_url == new_url:
            ok.append(checker)
            if OutputSettings.report_ok():
                log("%s%s/%s: %s [%s]",
                    emoji(":check_box_with_check:  "),
                    analyser, checker,
                    coloured("OK", "green"),
                    existing_url,
                    file=sys.stdout)
        elif new_url:
            updated[checker] = new_url
            log("%s%s/%s: %s [%s] -> [%s]",
                emoji(":sparkles:  "),
                analyser, checker,
                coloured("UPDATED", "yellow"),
                existing_url, new_url,
                file=sys.stdout)
        else:
            gone.append(checker)
            log("%s%s/%s: %s [%s]",
                emoji(":ghost:  "),
                analyser, checker,
                coloured("GONE", "red"),
                existing_url,
                file=sys.stdout)

    return ok, updated, new, gone, generator_skip, directive_skip


def print_generation(analyser: str,
                     original_urls: SingleLabels,
                     ok: List[str],
                     updated: SingleLabels,
                     new: SingleLabels):
    if not updated and not new:
        log("%s%s: Documentation for all %s %s is OK.",
            emoji(":magnifying_glass_tilted_left::check_mark_button:  "),
            analyser,
            coloured(f"{len(ok)}", "green"),
            plural(ok, "checker", "checkers"),
            )
    else:
        if updated:
            log("%s%s: %s %s changed documentation URL. (%s kept previous.)",
                emoji(":magnifying_glass_tilted_left::warning:  "),
                analyser,
                coloured(f"{len(updated)}", "yellow"),
                plural(updated, "checker", "checkers"),
                coloured(f"{len(ok)}", "green")
                if ok else coloured("0", "red"),
                )
        if new:
            log("%s%s: %s new %s did not have a `doc_url` label previously!",
                emoji(":magnifying_glass_tilted_left:"
                      ":magnifying_glass_tilted_right:  "),
                analyser,
                coloured(f"{len(new)}", "magenta"),
                plural(new, "checker", "checkers"),
                )

    for checker in sorted((ok if OutputSettings.report_ok() else []) +
                          list(updated.keys()) +
                          list(new.keys())):
        is_ok = (checker in ok) if OutputSettings.report_ok() else False
        is_updated = checker in updated
        icon = ":globe_showing_Europe-Africa:  " if is_ok \
            else ":bookmark:  " if is_updated \
            else ":world_map:  "
        colour = "green" if is_ok \
            else "yellow" if is_updated \
            else "magenta"
        url = original_urls[checker] if is_ok \
            else updated[checker] if is_updated \
            else new[checker]

        log("    %s· %s [%s]", emoji(icon), coloured(checker, colour), url)


def print_gone(analyser: str,
               gone: SingleLabels):
    if not gone:
        return

    log("%s%s: %s %s documentation gone.",
        emoji(":magnifying_glass_tilted_left::bar_chart:  "),
        analyser,
        coloured(f"{len(gone)}", "red"),
        plural(len(gone), "checker's", "checkers'"),
        )
    deque((log("    %s· %s [%s]",
               emoji(":skull_and_crossbones:  "),
               coloured(checker, "red"),
               gone[checker])
           for checker in sorted(gone)),
          maxlen=0)


def print_missing(analyser: str,
                  missing: List[str]):
    if not OutputSettings.report_missing():
        log("%s%s: %s %s will not have a `doc_url` label!",
            emoji(":magnifying_glass_tilted_left:"
                  ":magnifying_glass_tilted_right:  "),
            analyser,
            coloured(f"{len(missing)}", "yellow"),
            plural(missing, "checker", "checkers"),
            )
        if OutputSettings.report_missing():
            deque((log("    %s· %s ",
                       emoji(":bookmark:  "),
                       coloured(checker, "yellow"))
                   for checker in sorted(missing)),
                  maxlen=0)


def execute(analyser: str, generator_class: Type, labels: SingleLabels,
            checkers_to_skip: Set[str]) \
        -> Tuple[ReturnFlags, SingleLabels, Statistics]:
    """
    Runs one instance of the generation for a specific analyser.
    """
    status = cast(ReturnFlags, 0)
    missing = [checker for checker in labels if not labels[checker]]
    stats = Statistics(Analyser=analyser,
                       Generator=generator_class.kind,
                       Checkers=len(labels),
                       Generator_Skipped=None,
                       Directive_Skipped=None,
                       Missing=len(missing) if missing else None,
                       OK=None,
                       Updated=None,
                       Gone=None,
                       New=None,
                       All_Changed=0,
                       Not_Found=len(missing) if missing else None,
                       )
    urls: SingleLabels = {}
    ok, updated, new, gone, generator_skip, directive_skip = \
        run_generator(generator_class(analyser),
                      labels,
                      checkers_to_skip)
    print_generation(analyser, labels, ok, updated, new)
    urls.update(updated)
    urls.update(new)

    ok = set(ok)
    new = set(new)
    gone = set(gone)
    generator_skip = set(generator_skip)
    directive_skip = set(directive_skip)
    any_skip = generator_skip | directive_skip

    print_gone(analyser, {checker: labels[checker]
                          for checker in gone - any_skip})
    remaining_missing = list(labels.keys() - ok - updated.keys() - any_skip)
    print_missing(analyser, remaining_missing)
    stats = stats._replace(Generator_Skipped=len(generator_skip)
                           if generator_skip else None,
                           Directive_Skipped=len(directive_skip)
                           if directive_skip else None,
                           OK=len(ok) if ok else None,
                           Updated=len(updated) if updated else None,
                           Gone=len(gone) if gone else None,
                           New=len(new) if new else None,
                           All_Changed=len(urls),
                           Not_Found=len(remaining_missing),
                           )
    status |= (ReturnFlags.HadUpdate if updated else 0) \
        | (ReturnFlags.HadNew if new else 0) \
        | (ReturnFlags.HadGone if gone else 0) \
        | (ReturnFlags.RemainsMissing if remaining_missing else 0)

    return status, urls, stats
