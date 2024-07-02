#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Implementation of the user-facing entry point to the script."""
import argparse
import os
import pathlib
import sys
from typing import List, Optional, Set

from tabulate import tabulate

from codechecker_common.compatibility.multiprocessing import cpu_count
from codechecker_common.util import clamp

from ...checker_labels import SingleLabels, SkipDirectiveRespectStyle, \
    get_checker_labels_multiple, update_checker_labels
from ...codechecker import default_checker_label_dir
from ...exception import EngineError
from ...output import Settings as GlobalOutputSettings, \
    error, log, trace, coloured, emoji
from ...util import merge_if_no_collision, plural
from ... import fixit
from ..output import Settings as OutputSettings
from ..rules import Base as RuleBase, rules_visible_to_user
from . import tool


short_help: str = """
Verify various implicit invariants that should be upheld by the checker label
configuration files.
"""
description: str = (
    """
Verifies that the checker label configuration files adhere to some implicitly
considered invariants without which the behaviour of CodeChecker may become
unexpected.

The tool's output is primarily engineered to be human readable (with the added
sprinkle of colours and emojis).
If the output is not sent to an interactive terminal, the output switches to
the creation of a machine-readable output.

The return code of this tool is indicative of errors encountered during
execution.
'0' is returned for no errors (success), '1' indicates general errors,
'2' indicates configuration errors.
In every other case, the return value is the OR of a bitmask:
"""
    f"""
If there was a checker which failed invariant verification, the
'{tool.ReturnFlags.HadNotOK}' bit will be set.
If there was a checker which failed but could be automatically fixed, the
'{tool.ReturnFlags.HadFixed}' bit will be set.
"""
)
epilogue: str = ""


def args(parser: Optional[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    if not parser:
        parser = argparse.ArgumentParser(
            prog=__package__,
            description=description,
            epilog=epilogue,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "checker_label_dir",
        metavar="LABEL_DIR",
        nargs='?',
        default=default_checker_label_dir(),
        type=pathlib.PurePath,
        help="""
The configuration directory where the checker labels are available.
""")

    parser.add_argument(
        "-l", "--list-rules",
        dest="list_rules",
        action="store_true",
        help="""
List the available rules that the verification toolkit can verify.
This action disables running the verification itself!
""")

    parser.add_argument(
        "-j", "--jobs",
        metavar="COUNT",
        dest="jobs",
        type=int,
        default=cpu_count(),
        help="""
The number of parallel processes to use for verification of the invariants.
Defaults to all available logical cores.
""")

    parser.add_argument(
        "-f", "--fix",
        dest="apply_fixes",
        action="store_true",
        help="""
Apply the updates resulting from the automatic fixing of invariants
(whereever, but not in all cases, applicable) back into the input
configuration file.
""")

    filters = parser.add_argument_group("filter arguments")

    filters.add_argument(
        "--analysers", "--analyzers",
        metavar="ANALYSER",
        nargs='*',
        type=str,
        help="""
Filter for only the specified analysers before executing the verification.
Each analyser's configuration is present in exactly one JSON file, named
'<analyser-name>.json'.
If 'None' is given, automatically run for every found configuration file.
""")

    filters.add_argument(
        "--rules",
        metavar="RULE",
        nargs='*',
        type=str,
        help="""
Filter for only the specified invariant rules to verify (and fix).
If this argument is left unspecified, the default is to execute every
available rule.
""")

    output = parser.add_argument_group("output control arguments", """
These optional arguments allow enabling additional verbosity for the output
of the program.
By default, the tool tries to be the most concise possible, and only report
meaningful findings and encountered errors.
""")

    output.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        help="""
Shortcut to enable all verbosity options in this group that increase the
useful information presented on the output.
Does not enable any trace or debug information.
""")

    output.add_argument(
        "--report-ok",
        dest="report_ok",
        action="store_true",
        help="""
If set, the output will contain the "OK" reports for checkers which pass the
invariant verification steps.
By default, only errors are reported.
""")

    output.add_argument(
        "-vd", "--verbose-debug",
        dest="verbose_debug",
        action="store_true",
        help="Emit additional trace and debug output.")

    output.add_argument(
        "-vv", "--very-verbose",
        dest="very_verbose",
        action="store_true",
        help="""
Shortcut to enable all verbosity options, including trace and debug
information.
""")

    return parser


def _handle_package_args(args: argparse.Namespace):
    if not args.checker_label_dir:
        log("%sFATAL: Failed to find the checker label configuration "
            "directory, and it was not specified. "
            "Please specify!",
            emoji(":no_entry:  "))
        raise argparse.ArgumentError(None,
                                     "positional argument 'checker_label_dir'")
    if args.jobs < 0:
        log("%sFATAL: There can not be a non-positive number of jobs.",
            emoji(":no_entry:  "))
        raise argparse.ArgumentError(None, "-j/--jobs")
    OutputSettings.set_report_ok(args.report_ok or
                                 args.verbose or
                                 args.very_verbose)
    GlobalOutputSettings.set_trace(args.verbose_debug or args.very_verbose)


def _list_rules():
    for clazz in rules_visible_to_user:
        log(tabulate(
            tabular_data=[
                ("Name", clazz.kind),
                ("Description", clazz.description.replace('\n', ' ')),
                ("Supports fixes?",
                 emoji(":check_mark_button:  ") if clazz.supports_fixes
                 and sys.stderr.isatty()
                 else '+' if clazz.supports_fixes
                 else "")
            ],
            tablefmt="fancy_grid" if sys.stderr.isatty()
            else "grid"),
            file=sys.stderr)


def main(args: argparse.Namespace) -> Optional[int]:
    try:
        _handle_package_args(args)
    except argparse.ArgumentError:
        # Simulate argparse's return code of parse_args.
        raise SystemExit(2)

    if args.list_rules:
        _list_rules()
        return

    rc = 0
    statistics: List[tool.Statistics] = list()
    trace("Checking checker labels from '%s'", args.checker_label_dir)

    args.checker_label_dir = pathlib.Path(args.checker_label_dir)
    if not args.checker_label_dir.is_dir():
        error("'%s' is not a directory!", args.checker_label_dir)
        return 1

    rules: List[RuleBase] = list(filter(
        lambda clz: True if not args.rules else clz.kind in args.rules,
        rules_visible_to_user))
    if not rules:
        log("%sSkipping, no rules match the enable filter!",
            emoji(":no_littering:  "))
        return 1

    # FIXME: pathlib.Path.walk() is only available Python >= 3.12.
    for root, _, files in os.walk(args.checker_label_dir):
        root = pathlib.Path(root)

        for file in sorted(files):
            file = pathlib.Path(file)
            if file.suffix != ".json":
                continue
            analyser = file.stem
            if args.analysers and analyser not in args.analysers:
                continue

            path = root / file
            log("%sLoading '%s'... ('%s')",
                emoji(":magnifying_glass_tilted_left:  "),
                analyser,
                path)
            try:
                labels = get_checker_labels_multiple(path)
            except Exception:
                import traceback
                traceback.print_exc()

                error("Failed to obtain checker labels for '%s'!", analyser)
                continue

            process_count = clamp(1, args.jobs, len(labels)) \
                if len(labels) > 2 * args.jobs else 1
            fixes: Dict[str, List[fixit.FixAction]] = dict()
            try:
                tool.execute(analyser, rules, labels, process_count)
            except:
                pass
            # for invariant in rules:
                # print(invariant)
                # invariant.check("x", "y")

            raise Exception("fuck off")

            urls: SingleLabels = dict()
            conflicts: Set[str] = set()
            for generator_class in geners:
                log("%sGenerating '%s' as '%s' (%s)...",
                    emoji(":thought_balloon:  "),
                    analyser,
                    generator_class.kind,
                    generator_class)
                try:
                    status, generated_urls, statistic = tool.execute(
                        analyser,
                        generator_class,
                        labels,
                        checkers_to_skip
                    )
                    statistics.append(statistic)
                    rc = int(tool.ReturnFlags(rc) | status)
                except EngineError:
                    import traceback
                    traceback.print_exc()

                    error("Failed to execute generator '%s' (%s)",
                          generator_class.kind, generator_class)
                    rc = int(tool.ReturnFlags(rc) |
                             tool.ReturnFlags.GeneralError)
                    continue

                merge_if_no_collision(
                    urls, generated_urls, conflicts,
                    lambda checker, existing_fix, new_fix:
                    error("%s%s/%s: %s [%s] =/= [%s]", emoji(":collision:  "),
                          analyser, checker, coloured("FIX COLLISION", "red"),
                          existing_fix, new_fix)
                )

                if args.apply_fixes and urls:
                    log("%sUpdating %s %s for '%s'... ('%s')",
                        emoji(":writing_hand:  "),
                        coloured("%d" % len(urls), "green"),
                        plural(urls, "checker", "checkers"),
                        analyser,
                        path)
                    try:
                        update_checker_labels(
                            analyser, path, K_DocUrl, urls,
                            SkipDirectiveRespectStyle.AsPassed,
                            checkers_to_skip)
                    except Exception:
                        import traceback
                        traceback.print_exc()

                        error("Failed to write checker labels for '%s'!",
                              analyser)
                        continue

    log(tabulate(tabular_data=statistics,
                 headers=tuple(map(lambda s: s.replace('_', ' '),
                                   tool.Statistics._fields)),
                 tablefmt="fancy_outline" if sys.stderr.isatty()
                 else "outline"),
        file=sys.stderr)

    log("%s", repr(tool.ReturnFlags(rc)))
    return rc


if __name__ == "__main__":
    def _main():
        _args = args(None).parse_args()
        sys.exit(main(_args) or 0)
    _main()
