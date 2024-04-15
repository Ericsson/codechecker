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
import fnmatch
import os
import pathlib
import sys
from typing import List, Optional, Set

from tabulate import tabulate

from codechecker_common.compatibility.multiprocessing import cpu_count
from codechecker_common.util import clamp

from ...checker_labels import SingleLabels, get_checker_labels, \
    update_checker_labels
from ...codechecker import default_checker_label_dir
from ...output import Settings as GlobalOutputSettings, \
    error, log, trace, coloured, emoji
from ...util import merge_if_no_collision, plural
from ..output import Settings as OutputSettings
from ..verifiers import analyser_selection
from . import tool


short_help: str = """
Verify that the 'doc_url's are accessible by users, and update them to a fixed
version, if necessary.
"""
description: str = (
    """
Verify that the 'doc_url's are accessible by users, and update them to a fixed
version, if necessary.
This tool makes several HTTP requests to simulate a browser (a User-Agent)
querying for checker documentations, as if a user was clicking the URLs present
on the CodeChecker UI.
Found analysers and checkers are verified, and if the verification fails,
attempts to resolve to a working URL (often by fixing typos and finding an
older release of the analysers where the requested page still exists).

Following execution, the tool prints a statistics output automatically.
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
Having found checkers without a 'doc_url' label will set the bit
'{tool.ReturnFlags.HAD_MISSING}'.
Having found checkers that have a "Not OK" label will set the bit
'{tool.ReturnFlags.HAD_NOT_OK}'.
Having found checkers that were "Not OK" but managed to obtain a fixed,
working URL will set the bit '{tool.ReturnFlags.HAD_FOUND}'.
Having found checkers that were "Not OK" and failed the attempted
automatic fixing routing will set the bit '{tool.ReturnFlags.HAD_GONE}'.
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
        "-j", "--jobs",
        metavar="COUNT",
        dest="jobs",
        type=int,
        default=cpu_count(),
        help="""
The number of parallel processes to use for querying the validity of the
"documentation URLs.
Defaults to all available logical cores.
""")

    behaviour = parser.add_argument_group("behaviour arguments", """
These optional arguments allow fine-tuning the steps executed by the
verification logic.
Unlike filters, which change what inputs are considered for verification, the
behavioural arguments change the executed logic for all considered inputs.
""")

    behaviour.add_argument(
        "--reset-to-upstream",
        dest="reset_to_upstream",
        action="store_true",
        help="""
Where applicable to the analyser and known how to do so, reset every checker's
documentation URL to what it would be if it pointed to the upstream version,
even if it does not actually do so.
This allows both the verification of the "URL fixing" logic, and to uncover
potentially old or outdated documentation URLs.
""")

    fix = behaviour.add_mutually_exclusive_group(required=False)

    fix.add_argument(
        "-f", "--fix",
        dest="apply_fixes",
        action="store_true",
        help="""
Apply and update the fixed 'doc_url's for cases which were "Not OK" but the
fixing heuristics managed to find a proper result back into the input
configuration file.
""")

    fix.add_argument(
        "--skip-fixes",
        dest="skip_fixes",
        action="store_true",
        help="""
Completely skip executing the "URL fixing" phase in which the tool would search
for a version of the URL where the documentation is available to the user.
Instead, stop and quit after gathering "OK" and "Not OK" status.
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
        "--checkers",
        metavar="CHECKER",
        nargs='*',
        type=str,
        help=f"""
Filter for only the specified checkers before executing the verification.
This filter matches only for the checker's name (as present in the
configuration file), and every checker of every candidate analyser is matched
against.
It is not an error to specify filters that do not match anything.
It is possible to match entire patterns of names using the '?' and '*'
wildcards, as understood by the 'fnmatch' library, see
"https://docs.python.org/{sys.version_info[0]}.{sys.version_info[1]}/library/\
fnmatch.html#fnmatch.fnmatchcase"
for details.
Depending on your shell, you might have to specify wildcards in single quotes,
e.g., 'alpha.*', to prevent the shell from globbing first!
If 'None' is given, automatically run for every checker.
""")

    output = parser.add_argument_group("output control arguments", """
These optional arguments allow enabling additional verbosity for the output
of the program.
By default, the tool tries to be the most concise possible, and only report
negative findings ("Not OK" results) and encountered errors.
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
do not have any 'doc_url' label at all ("MISSING").
""")

    output.add_argument(
        "--report-ok",
        dest="report_ok",
        action="store_true",
        help="""
If set, the output will contain the "OK" reports for checkers that successfully
verified.
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


def _handle_package_args(args_: argparse.Namespace):
    if not args_.checker_label_dir:
        log("%sFATAL: Failed to find the checker label configuration "
            "directory, and it was not specified. "
            "Please specify!",
            emoji(":no_entry:  "))
        raise argparse.ArgumentError(None,
                                     "positional argument 'checker_label_dir'")
    if args_.jobs < 0:
        log("%sFATAL: There can not be a non-positive number of jobs.",
            emoji(":no_entry:  "))
        raise argparse.ArgumentError(None, "-j/--jobs")
    OutputSettings.set_report_missing(args_.report_missing or
                                      args_.verbose or
                                      args_.very_verbose)
    OutputSettings.set_report_ok(args_.report_ok or
                                 args_.verbose or
                                 args_.very_verbose)
    GlobalOutputSettings.set_trace(args_.verbose_debug or args_.very_verbose)


def main(args_: argparse.Namespace) -> Optional[int]:
    try:
        _handle_package_args(args_)
    except argparse.ArgumentError as err:
        # Simulate argparse's return code of parse_args().
        raise SystemExit(2) from err

    rc = 0
    statistics: List[tool.Statistics] = []
    trace("Checking checker labels from '%s'", args_.checker_label_dir)

    args_.checker_label_dir = pathlib.Path(args_.checker_label_dir)
    if not args_.checker_label_dir.is_dir():
        error("'%s' is not a directory!", args_.checker_label_dir)
        return 1

    # FIXME: pathlib.Path.walk() is only available Python >= 3.12.
    for root, _, files in os.walk(args_.checker_label_dir):
        root = pathlib.Path(root)

        for file in sorted(files):
            file = pathlib.Path(file)
            if file.suffix != ".json":
                continue
            analyser = file.stem
            if args_.analysers and analyser not in args_.analysers:
                continue

            path = root / file
            log("%sLoading '%s'... ('%s')",
                emoji(":magnifying_glass_tilted_left:  "),
                analyser,
                path)
            try:
                labels = get_checker_labels(analyser, path, "doc_url")
            except Exception:
                import traceback
                traceback.print_exc()

                error("Failed to obtain checker labels for '%s'!", analyser)
                continue

            if args_.checkers:
                labels = {checker: url
                          for checker, url in labels.items()
                          for filter_ in args_.checkers
                          if fnmatch.fnmatchcase(checker, filter_)}
            if not labels:
                filt = " or match the \"--checkers\" %s" + \
                    plural(args_.checkers, "filter", "filters") \
                    if args_.checkers else ""
                log(f'{emoji(":cup_with_straw:  ")}'
                    f'No checkers are configured{filt}.')
                continue

            process_count = clamp(1, args_.jobs, len(labels)) \
                if len(labels) > 2 * args_.jobs else 1
            fixes: SingleLabels = {}
            conflicts: Set[str] = set()
            for verifier in analyser_selection.select_verifier(analyser,
                                                               labels):
                log("%sVerifying '%s' as '%s' (%s)...",
                    emoji(":thought_balloon:  "),
                    analyser,
                    verifier.kind, verifier)
                status, local_fixes, statistic = tool.execute(
                    analyser,
                    verifier,
                    labels,
                    process_count,
                    args_.skip_fixes,
                    args_.reset_to_upstream,
                    )
                statistics.append(statistic)
                rc = int(tool.ReturnFlags(rc) | status)

                merge_if_no_collision(
                    fixes, local_fixes, conflicts,
                    lambda checker, existing_fix, new_fix:
                    error("%s%s/%s: %s [%s] =/= [%s]", emoji(":collision:  "),
                          analyser, checker, coloured("FIX COLLISION", "red"),
                          existing_fix, new_fix)
                )
                if args.apply_fixes and fixes:
                    log("%sUpdating %s %s for '%s'... ('%s')",
                        emoji(":writing_hand:  "),
                        coloured(len(fixes), "green"),
                        plural(fixes, "checker", "checkers"),
                        analyser,
                        path)
                    try:
                        update_checker_labels(analyser, path, "doc_url", fixes)
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
