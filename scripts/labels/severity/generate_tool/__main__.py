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
from functools import partial
import os
import pathlib
import sys
from typing import List, Optional, Set

from tabulate import tabulate

from ...checker_labels import SingleLabels, SkipDirectiveRespectStyle, \
    get_checker_labels, get_checkers_with_ignore_of_key, update_checker_labels
from ...codechecker import default_checker_label_dir
from ...exception import EngineError
from ...output import Settings as GlobalOutputSettings, \
    error, log, trace, coloured, emoji
from ...util import merge_if_no_collision, plural
from ..generators import analyser_selection
from ..output import Settings as OutputSettings
from . import tool


short_help: str = """
Auto-generate 'severity' labels for checkers based on analyser-specific
information and heuristics.
"""
description: str = (
    """
Automatically generate the 'severity' categorisation labels from a known and
available, analyser-specific (this tool does not support a "generic" execution
pattern) heuristic.
This could be a "Table of Contents" (ToC) structure officially maintained by
the analyser, or an another form of similar classification, or an entirely
customised classifier heuristic implemented only by CodeChecker.

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
If there was a checker which already had a 'severity' but now the generator
generated a different value, the '{tool.ReturnFlags.HadUpdate}' bit will be
set.
If there were checkers without a 'severity' (or without any labels at all) but
the tool generated a valid 'severity' for them, the '{tool.ReturnFlags.HadNew}'
bit will be set.
If there are checkers with 'severity' labels that are no longer available in
the generated result, the '{tool.ReturnFlags.HadGone}' bit will be set.
In case after the analysis there are still checkers which do not have a
'severity' at all, the '{tool.ReturnFlags.RemainsMissing}' bit will be set.
"""
)
epilogue: str = ""


K_Severity: str = "severity"


def arg_parser(parser: Optional[argparse.ArgumentParser]) \
        -> argparse.ArgumentParser:
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
        "-f", "--fix",
        dest="apply_fixes",
        action="store_true",
        help="""
Apply the updated or generated 'severity' labels back into the input
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
        "--report-missing",
        dest="report_missing",
        action="store_true",
        help="""
If set, the output will contain an additional list that details which checkers
remain in the configuration file without an appropriate 'severity' label
("MISSING").
""")

    output.add_argument(
        "--report-ok",
        dest="report_ok",
        action="store_true",
        help="""
If set, the output will contain the "OK" reports for checkers which
severity classification is already the same as would be generated by this tool.
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
    OutputSettings.set_report_missing(args.report_missing or
                                      args.verbose or
                                      args.very_verbose)
    OutputSettings.set_report_ok(args.report_ok or
                                 args.verbose or
                                 args.very_verbose)
    GlobalOutputSettings.set_trace(args.verbose_debug or args.very_verbose)


def _emit_collision_error(analyser: str,
                          checker: str,
                          existing_fix: str,
                          new_fix: str):
    error("%s%s/%s: %s [%s] =/= [%s]", emoji(":collision:  "),
          analyser, checker,
          coloured("FIX COLLISION", "red"),
          existing_fix, new_fix)


def main(args: argparse.Namespace) -> Optional[int]:
    try:
        _handle_package_args(args)
    except argparse.ArgumentError as arg_err:
        # Simulate argparse's return code of parse_args.
        raise SystemExit(2) from arg_err

    rc = 0
    statistics: List[tool.Statistics] = []
    trace("Checking checker labels from '%s'", args.checker_label_dir)

    args.checker_label_dir = pathlib.Path(args.checker_label_dir)
    if not args.checker_label_dir.is_dir():
        error("'%s' is not a directory!", args.checker_label_dir)
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
                checkers_to_skip = get_checkers_with_ignore_of_key(
                    path, K_Severity)
                labels = get_checker_labels(
                    analyser, path, K_Severity,
                    SkipDirectiveRespectStyle.AS_PASSED, checkers_to_skip)
            except Exception:
                import traceback
                traceback.print_exc()

                error("Failed to obtain checker labels for '%s'!", analyser)
                continue

            generators = list(analyser_selection.select_generator(analyser))
            if not generators:
                log("%sSkipped '%s', no generator implementation!",
                    emoji(":no_littering:  "),
                    analyser)
                continue

            severities: SingleLabels = {}
            conflicts: Set[str] = set()
            for generator_class in generators:
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
                        checkers_to_skip,
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

                merge_if_no_collision(severities, generated_urls, conflicts,
                                      partial(_emit_collision_error, analyser))

                if args.apply_fixes and severities:
                    log("%sUpdating %s %s for '%s'... ('%s')",
                        emoji(":writing_hand:  "),
                        coloured(f"{len(severities)}", "green"),
                        plural(severities, "checker", "checkers"),
                        analyser,
                        path)
                    try:
                        update_checker_labels(
                            analyser, path, K_Severity, severities,
                            SkipDirectiveRespectStyle.AS_PASSED,
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
        args = arg_parser(None).parse_args()
        sys.exit(main(args) or 0)
    _main()
