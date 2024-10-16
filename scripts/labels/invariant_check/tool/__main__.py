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
from copy import deepcopy
import fnmatch
import operator
import os
import pathlib
import sys
from typing import List, Optional, Type

from tabulate import tabulate

from codechecker_common.compatibility.multiprocessing import cpu_count
from codechecker_common.util import clamp

from ...checker_labels import apply_label_fixes, \
    get_checker_labels_multiple, update_checker_labels_multiple_overwrite
from ...codechecker import default_checker_label_dir
from ...output import Settings as GlobalOutputSettings, \
    error, log, trace, coloured, emoji
from ...util import plural
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
        help=f"""
Filter for only the specified invariant rules to verify (and fix).
It is not an error to specify filters that do not match anything.
It is possible to match entire patterns of names using the '?' and '*'
wildcards, as understood by the 'fnmatch' library, see
"https://docs.python.org/{sys.version_info[0]}.{sys.version_info[1]}/library/\
fnmatch.html#fnmatch.fnmatchcase"
for details.
Depending on your shell, you might have to specify wildcards in single quotes,
e.g., 'profile.*', to prevent the shell from globbing first!
If 'None' is given, automatically run for every checker.
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


def _list_rules(rules: List[Type[RuleBase]]):
    for clazz in rules:
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
    except argparse.ArgumentError as arg_err:
        # Simulate argparse's return code of parse_args.
        raise SystemExit(2) from arg_err

    rules: List[Type[RuleBase]] = [rule
                                   for rule in rules_visible_to_user
                                   for filter_ in args.rules
                                   if fnmatch.fnmatchcase(rule.kind, filter_)]
    rules.sort(key=operator.attrgetter("kind"))
    if args.list_rules:
        _list_rules(rules)
        return 0
    if not rules:
        log("%sSkipping, no rules match the enable filter!",
            emoji(":no_littering:  "))
        return 1

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
                labels = get_checker_labels_multiple(path)
            except Exception:
                import traceback
                traceback.print_exc()

                error("Failed to obtain checker labels for '%s'!", analyser)
                continue

            process_count = clamp(1, args.jobs, len(labels)) \
                if len(labels) > 2 * args.jobs else 1

            log("%sVerifying '%s' ...",
                emoji(":thought_balloon:  "),
                analyser)
            status, stats, fixes = tool.execute(
                analyser,
                rules,
                labels,
                process_count)
            statistics.extend(stats)
            rc = int(tool.ReturnFlags(rc) | status)

            if args.apply_fixes and fixes:
                all_fix_count = sum((len(fs) for fs in fixes.values()))
                log("%sApplying %s %s to %s %s for '%s'... ('%s')",
                    emoji(":writing_hand:  "),
                    coloured(f"{all_fix_count}", "green"),
                    plural(all_fix_count, "fix", "fixes"),
                    coloured(f"{len(fixes)}", "green"),
                    plural(fixes, "checker", "checkers"),
                    analyser,
                    path)
                try:
                    new_labels = apply_label_fixes(deepcopy(labels), fixes)
                except Exception:
                    import traceback
                    traceback.print_exc()

                    error("Failed to fix-up checker labels for '%s'!",
                          analyser)
                    continue

                try:
                    update_checker_labels_multiple_overwrite(
                        analyser, path, new_labels)
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
