#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Checks the config/labels/<analyzer>.json files against the list of checkers
reported from actually inquiring the analyzers, and reports if there is a
checker missing from the config file.
"""
import argparse
import json
import sys


def filter_namelist(names, filter_prefixes=None, ignore_prefixes=None,
                    ignore_suffixes=None):
    """Filters the names list for entries that match the filter_prefixes,
    and do not match the ignore_prefixes or ignore_suffixes.
    """
    ret = set(names)
    if filter_prefixes:
        ret = set(e for e in ret
                  if e.startswith(tuple(filter_prefixes)))
    if ignore_prefixes:
        ret = set(e for e in ret
                  if not e.startswith(tuple(ignore_prefixes)))
    if ignore_suffixes:
        ret = set(e for e in ret
                  if not e.endswith(tuple(ignore_suffixes)))
    return ret


def main():
    parser = argparse.ArgumentParser(
        description="""
Check a list of checkers (usually the output of "CodeChecker checkers -o rows")
and the checker severity map for missing or stale entries.
""",
        epilog="""
The tool exits with 0 if the list of checkers is fully covered.
An exit status of 1 is reserved for errors escaping the interpreter.
An exit status of 2 indicates bad invocation (from 'argparse').
An exit status of 4 indicates that checkers were removed from upstream but
still have a severity, and 8 indicates that there are checkers missing
severity settings.
An exit status of 12 (4 + 8) indicates both.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checker_name_list",
                        type=argparse.FileType('rt'),
                        help="The file that lists the checkers available in "
                             "the analyzer(s). The file must exist!")
    parser.add_argument("checker_label_map",
                        type=argparse.FileType('rt'),
                        nargs='+',
                        help="Path of configuration files that list labels "
                             "for checkers. More files can be specified. All "
                             "files must exist!")

    existing = parser.add_argument_group(
        "filtering options for existing (only configured) checks")
    existing.add_argument("--report-removed",
                          dest="report_removed",
                          action="store_true",
                          help="Whether to report checks that went missing, "
                               "i.e. only exist in the configuration file(s) "
                               "but not in the analyzers.")
    existing.add_argument("--existing-filter",
                          nargs='*',
                          default=list(),
                          help="The checker prefixes (such as \"alpha.\" or "
                               "\"debug.\") to positively filter for when "
                               "searching for removed checkers.")
    existing.add_argument("--existing-ignore",
                          nargs='*',
                          default=list(),
                          help="The checker prefixes (such as \"alpha.\" or "
                               "\"debug.\") to ignore from the coverage check "
                               "when searching for removed checkers.")
    existing.add_argument("--existing-ignore-suffix",
                          nargs='*',
                          default=list(),
                          help="The checker suffixes (such as \"Sanitizer\""
                               "or \"-name\") to ignore from the coverage "
                               "check when searching for removed checkers.")

    new = parser.add_argument_group(
        "filtering options for new (not configured) checks")
    new.add_argument("--no-report-new",
                     dest="report_new",
                     action="store_false",
                     help="Whether to *NOT* report checks that are new: "
                          "they do not exist in the configuration "
                          "file(s), only in the analyzers.")
    new.add_argument("--new-filter",
                     nargs='*',
                     default=list(),
                     help="The checker prefixes (such as \"alpha.\" or "
                          "\"debug.\") to positively filter for when "
                          "searching for unknown/new checkers.")
    new.add_argument("--new-ignore",
                     nargs='*',
                     default=list(),
                     help="The checker prefixes (such as \"alpha.\" or "
                          "\"debug.\") to ignore from the coverage check "
                          "when searching for unknown/new checkers.")
    new.add_argument("--new-ignore-suffix",
                     nargs='*',
                     default=list(),
                     help="The checker suffixes (such as \"Sanitizer\" or "
                          "\"-name\") to ignore from the coverage check "
                          "when searching for unknown/new checkers.")

    args = parser.parse_args()

    dumped_checkers = set(line.strip() for line in args.checker_name_list)
    available_checkers = filter_namelist(dumped_checkers,
                                         args.new_filter,
                                         args.new_ignore,
                                         args.new_ignore_suffix)

    all_known_checkers = set()
    for config in args.checker_label_map:
        checkers_in_cfg = json.load(config)["labels"].keys()
        checkers = filter_namelist(checkers_in_cfg,
                                   args.existing_filter,
                                   args.existing_ignore,
                                   args.existing_ignore_suffix)
        all_known_checkers.update(checkers)

    print("Checkers REMOVED from upstream, with CodeChecker still "
          "assigning labels:")
    any_removed = False
    if args.report_removed:
        for removed_checker in sorted(all_known_checkers - available_checkers):
            print(" - {}".format(removed_checker))
            any_removed = True
        if not any_removed:
            print("    No such results.")
    else:
        print("Skipped! Specify '--report-removed' to execute.")

    print()

    print("Checkers ADDED to upstream, without labels in CodeChecker:")
    any_new = False
    if args.report_new:
        for missing_checker in sorted(available_checkers - all_known_checkers):
            print(" + {}".format(missing_checker))
            any_new = True
        if not any_new:
            print("    No such results.")
    else:
        print("Skipped! Do **NOT** specify '--no-report-new' to execute.")

    return_code = 0
    if any_removed:
        return_code += 4
    if any_new:
        return_code += 8
    return return_code


if __name__ == '__main__':
    sys.exit(main())
