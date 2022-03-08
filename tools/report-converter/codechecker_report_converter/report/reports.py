# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import sys

from typing import Any, Callable, Iterable, List, Optional, Set

from codechecker_report_converter.report import Report, SkipListHandlers
from codechecker_report_converter.report.hash import get_report_path_hash

LOG = logging.getLogger('report-converter')


class GenericSuppressHandler:
    get_suppressed: Callable[[Any, Report], bool]
    store_suppress_bug_id: Callable[[Any, str, str, str, str], bool]


def get_mentioned_original_files(reports: List[Report]) -> Set[str]:
    """ Get all mentioned files from the given reports. """
    files = set()

    for report in reports:
        files.update(report.original_files)

    return files


def get_changed_files(reports: List[Report]):
    """ Get all changed files from the given reports. """
    changed_files = set()

    for report in reports:
        changed_files.update(report.changed_files)

    return changed_files


def dump_changed_files(changed_files: Set[str]):
    """ Dump changed files. """
    if not changed_files:
        return None

    file_paths = '\n'.join([' - ' + f for f in changed_files])
    LOG.warning("The following source file contents changed or missing since "
                "the latest analysis:\n%s\nPlease re-analyze your "
                "project to update the reports!", file_paths)


def skip(
    reports: List[Report],
    processed_path_hashes: Optional[Set[str]] = None,
    skip_handlers: Optional[SkipListHandlers] = None,
    suppr_handler: Optional[GenericSuppressHandler] = None,
    src_comment_status_filter: Optional[Iterable[str]] = None
) -> List[Report]:
    """ Skip reports. """
    kept_reports = []
    for report in reports:
        if skip_handlers and report.skip(skip_handlers):
            LOG.debug("Skip report because file path (%s) is on the skip "
                      "list.", report.file.path)
            continue

        if suppr_handler and suppr_handler.get_suppressed(report):
            LOG.debug("Suppressed by suppress file: %s:%s [%s] %s",
                      report.file.original_path, report.line,
                      report.checker_name, report.report_hash)
            continue

        if report.source_code_comments:
            if len(report.source_code_comments) > 1:
                LOG.error("Multiple source code comment can be found for '%s' "
                          "checker in '%s' at line %d.", report.checker_name,
                          report.file.original_path, report.line)
                sys.exit(1)

            if suppr_handler:
                if not report.report_hash:
                    LOG.warning("Can't store suppress information for report "
                                "because no report hash is set: %s", report)
                    continue

                source_code_comment = report.source_code_comments[0]
                suppr_handler.store_suppress_bug_id(
                    report.report_hash,
                    report.file.name,
                    source_code_comment.message,
                    source_code_comment.status)

            if src_comment_status_filter and \
                    not report.check_source_code_comments(
                        src_comment_status_filter):
                LOG.debug("Filtered out by --review-status filter option: "
                          "%s:%s [%s] %s [%s]",
                          report.file.original_path, report.line,
                          report.checker_name, report.report_hash,
                          report.review_status)
                continue
        else:
            if src_comment_status_filter and \
                    'unreviewed' not in src_comment_status_filter:
                LOG.debug("Filtered out by --review-status filter option: "
                          "%s:%s [%s] %s [unreviewed]",
                          report.file.original_path, report.line,
                          report.checker_name, report.report_hash)
                continue

        if processed_path_hashes is not None:
            report_path_hash = get_report_path_hash(report)
            if report_path_hash in processed_path_hashes:
                LOG.debug("Not showing report because it is a deduplication "
                          "of an already processed report!")
                LOG.debug("Path hash: %s", report_path_hash)
                LOG.debug(report)
                continue

            processed_path_hashes.add(report_path_hash)

        kept_reports.append(report)

    return kept_reports
