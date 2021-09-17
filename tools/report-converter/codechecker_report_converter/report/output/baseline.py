# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" CodeChecker baseline output helpers. """

import logging
from typing import Iterable, List, Set, TextIO

from codechecker_report_converter.report import Report


LOG = logging.getLogger('report-converter')


def __get_report_hashes(f: TextIO) -> List[str]:
    """ Get report hashes from the given file. """
    return [h.strip() for h in f.readlines() if h]


def check(file_path: str) -> bool:
    """ True if the given file path is a baseline file. """
    return file_path.endswith('.baseline')


def get_report_hashes(
    baseline_file_paths: Iterable[str]
) -> Set[str]:
    """ Get uniqued hashes from baseline files. """
    report_hashes = set()
    for file_path in baseline_file_paths:
        with open(file_path, mode='r', encoding='utf-8', errors="ignore") as f:
            report_hashes.update(__get_report_hashes(f))

    return report_hashes


def convert(reports: Iterable[Report]) -> List[str]:
    """ Convert the given reports to CodeChecker baseline format.

    Returns a list of sorted unique report hashes.
    """
    return sorted(set(
        r.report_hash for r in reports if r.report_hash is not None))


def write(file_path: str, report_hashes: Iterable[str]):
    """ Create a new baseline file or extend an existing one with the given
    report hashes in the given output directory. It will remove the duplicates
    and also sort the report hashes before writing it to a file.
    """
    with open(file_path, mode='a+', encoding='utf-8', errors="ignore") as f:
        f.seek(0)
        old_report_hashes = __get_report_hashes(f)
        new_report_hashes = set(report_hashes) - set(old_report_hashes)

        if not new_report_hashes:
            LOG.info("Baseline file (%s) is up-to-date.", file_path)
            return

        if old_report_hashes:
            LOG.info("Merging existing baseline file: %s", file_path)
        else:
            LOG.info("Creating new baseline file: %s", file_path)

        LOG.info("Total number of old report hashes: %d",
                 len(old_report_hashes))
        LOG.info("Total number of new report hashes: %d",
                 len(new_report_hashes))

        LOG.debug("New report hashes: %s", sorted(new_report_hashes))

        f.seek(0)
        f.truncate()
        f.write("\n".join(sorted(
            set([*old_report_hashes, *report_hashes]))))
