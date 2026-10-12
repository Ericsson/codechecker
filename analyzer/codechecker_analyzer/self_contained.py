# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Post-process an analysis output directory to make it self-contained
(relocatable).

For every plist result file in the output directory, this copies each source
and header file referenced by the reports into a 'sources/' directory under the
output path, and rewrites the plist's file list to reference those copies using
paths relative to the plist file's own directory.

Because the plist parser resolves the entries of its 'files' array relative to
the directory of the plist file itself (see
codechecker_report_converter.report.parser.plist.get_file_index_map), the
resulting output directory can be moved to another machine and 'CodeChecker
parse' will still find the referenced sources.
"""

import os
import shutil

from codechecker_report_converter.report import File, Report
from codechecker_report_converter.report import report_file
from codechecker_report_converter.report.parser import plist

from codechecker_common import logger

LOG = logger.get_logger("system")

# Name of the directory (relative to the output path) that collects the copied
# source files.
SOURCES_DIR_NAME = "sources"


def __mirror_path_under_sources(original_path: str) -> str:
    """
    Return the path, relative to the sources directory, under which the given
    absolute source file should be stored.

    The absolute path is mirrored under the sources directory so that files
    with the same base name coming from different directories do not collide.
    On POSIX '/home/user/a.c' becomes 'home/user/a.c'. A possible Windows
    drive letter (e.g. 'C:') is turned into a plain directory component.
    """
    drive, tail = os.path.splitdrive(original_path)

    tail = tail.lstrip("/\\")

    if drive:
        # 'C:' -> 'C'
        drive = drive.rstrip(":").rstrip("\\/")
        return os.path.join(drive, tail)

    return tail


def __copy_into_sources(original_path: str, sources_dir: str) -> str | None:
    """
    Copy the file at 'original_path' into 'sources_dir', mirroring its absolute
    path. Return the absolute path of the copy, or None if the source file does
    not exist or could not be copied.
    """
    if not os.path.isfile(original_path):
        LOG.debug(
            "Referenced file does not exist, skipping: %s", original_path
        )
        return None

    rel_under_sources = __mirror_path_under_sources(original_path)
    dest_path = os.path.join(sources_dir, rel_under_sources)

    if os.path.exists(dest_path):
        return dest_path

    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(original_path, dest_path)
    except OSError as ex:
        LOG.warning(
            "Failed to copy referenced file '%s' into the "
            "self-contained output: %s",
            original_path,
            ex,
        )
        return None

    return dest_path


def __iter_report_files(report: Report):
    """
    Yield every File object referenced by the report.

    Based on the files property in
    codechecker_report_converter.report.__init__

    We cannot use the files property directly,
    because its side effects result in a Key error.
    """
    yield report.file
    yield from (e.file for e in report.bug_path_events)
    yield from (p.file for p in report.bug_path_positions)
    yield from (n.file for n in report.notes)
    yield from (m.file for m in report.macro_expansions)


def __relocate_reports(
    reports: list[Report],
    plist_dir: str,
    sources_dir: str,
) -> bool:
    """
    Copy every file referenced by 'reports' into 'sources_dir' and swap the
    File objects on the reports for new ones carrying a path relative to
    'plist_dir'.

    Return True if at least one file was relocated (i.e. the plist needs to be
    rewritten).
    """
    changed = False
    # Only move files once
    file_cache: dict[str, File] = {}
    for report in reports:
        original_paths = {f.original_path for f in __iter_report_files(report)}

        for original_path in original_paths:
            if original_path in file_cache:
                replacement = file_cache[original_path]
            else:
                dest_path = __copy_into_sources(original_path, sources_dir)
                if dest_path is None:
                    continue

                rel_to_plist = os.path.relpath(dest_path, plist_dir)
                replacement = File(rel_to_plist)
                file_cache[original_path] = replacement

            __rewrite_report_file(report, original_path, replacement)
            changed = True

    return changed


def __rewrite_report_file(
    report: Report, original_path: str, replacement: File
):
    """
    Replace every File on the given report whose original_path matches
    'original_path' with 'replacement'.
    """
    if report.file.original_path == original_path:
        report.file = replacement

    for event in report.bug_path_events:
        if event.file.original_path == original_path:
            event.file = replacement

    for position in report.bug_path_positions:
        if position.file.original_path == original_path:
            position.file = replacement

    for note in report.notes:
        if note.file.original_path == original_path:
            note.file = replacement

    for macro in report.macro_expansions:
        if macro.file.original_path == original_path:
            macro.file = replacement


def make_plist_self_contained(plist_file_path: str, sources_dir: str) -> bool:
    """
    Rewrite a single plist file to be self-contained.

    Return True if the plist was rewritten, False otherwise.
    """
    plist_dir = os.path.dirname(os.path.abspath(plist_file_path))

    reports = report_file.get_reports(plist_file_path)
    if not reports:
        return False

    changed = __relocate_reports(reports, plist_dir, sources_dir)

    if not changed:
        return False

    report_file.create(plist_file_path, reports)
    return True


def make_self_contained(output_path: str):
    """
    Make every plist result file in 'output_path' self-contained.

    Copies all referenced source files into '<output_path>/sources' and
    rewrites the plist files to reference them relative to their own location.
    """
    sources_dir = os.path.join(output_path, SOURCES_DIR_NAME)

    for root_dir, _, file_names in os.walk(output_path):
        # Do not descend into the sources directory we are populating.
        if os.path.abspath(root_dir) == os.path.abspath(sources_dir):
            continue

        for file_name in file_names:
            if not file_name.endswith(f".{plist.EXTENSION}"):
                continue

            plist_file_path = os.path.join(root_dir, file_name)
            make_plist_self_contained(plist_file_path, sources_dir)
