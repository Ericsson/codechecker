# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parse the plist output of an analyzer and convert it to a report for
further processing.

With the newer clang releases more information is available in the plist files.

* Before Clang v3.7:
  - Checker name is misssing (tried to detect based on the description)
  - Report hash is not avilable (generated based on the report path elemens
    see report handling and plist parsing modules for more details.

* Clang v3.7:
  - Checker name is available in the plist
  - Report hash is still missing (hash is generated as before)

* After Clang v3.8:
  - Checker name is available
  - Report hash is available

* Clang-tidy:
  - No plist format is provided in the available releases (v3.9 and before)
  - Checker name can be parsed from the output
  - Report hash is generated based on the report path elements the same way as
    for Clang versions before v3.7

"""

import os
import plistlib
import sys
import traceback
from xml.parsers.expat import ExpatError

from libcodechecker.logger import LoggerFactory

from libcodechecker.report import Report
from libcodechecker.report import generate_report_hash

LOG = LoggerFactory.get_new_logger('PLIST_PARSER')


def get_checker_name(diagnostic, path=""):
    """
    Check if checker name is available in the report.
    Checker name was not available in older clang versions before 3.7.
    """
    checker_name = diagnostic.get('check_name')
    if not checker_name:
        LOG.info("Check name wasn't found in the plist file '%s'. "
                 "Read the user guide!" % path)
        checker_name = "unknown"
    return checker_name


def get_report_hash(diagnostic, source_file):
    """
    Check if checker name is available in the report.
    Checker hash was not available in older clang versions before 3.8.
    """

    report_hash = diagnostic.get('issue_hash_content_of_line_in_context')
    if not report_hash:
        # Generate hash value if it is missing from the report.
        report_hash \
            = generate_report_hash(diagnostic['path'],
                                   source_file,
                                   get_checker_name(diagnostic))
    return report_hash


def parse_plist(path, source_root=None):
    """
    Parse the reports from a plist file.
    One plist file can contain multiple reports.
    """
    LOG.debug("Parsing plist: " + path)

    reports = []
    files = []
    try:
        plist = plistlib.readPlist(path)

        files = plist['files']

        for diag in plist['diagnostics']:

            available_keys = diag.keys()

            main_section = {}
            for key in available_keys:
                # Skip path it is handled separately.
                if key != 'path':
                    main_section.update({key: diag[key]})

            # We need to extend information for plist files generated
            # by older clang version (before 3.7).
            main_section['check_name'] = get_checker_name(diag, path)

            # We need to extend information for plist files generated
            # by older clang version (before 3.8).
            file_path = files[diag['location']['file']]
            if source_root:
                file_path = os.path.join(source_root, file_path.lstrip('/'))

            main_section['issue_hash_content_of_line_in_context'] = \
                get_report_hash(diag, file_path)

            bug_path_items = [item for item in diag['path']]

            report = Report(main_section, bug_path_items)
            reports.append(report)

    except (ExpatError, TypeError, AttributeError) as err:
        LOG.error('Failed to process plist file: ' + path +
                  ' wrong file format?')
        LOG.error(err)
    except IndexError as iex:
        LOG.error('Indexing error during processing plist file ' +
                  path)
        LOG.error(type(iex))
        LOG.error(repr(iex))
        _, _, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    except Exception as ex:
        LOG.error('Error during processing reports from the plist file: ' +
                  path)
        traceback.print_exc()
        LOG.error(type(ex))
        LOG.error(ex)
    finally:
        return files, reports


def fids_in_range(rng):
    """
    Get the file ids from a range.
    """
    fids = []
    for r in rng:
        for l in r:
            fids.append(l['file'])
    return fids


def fids_in_edge(edges):
    """
    Get the file ids from an edge.
    """
    fids = []
    for e in edges:
        start = e['start']
        end = e['end']
        for l in start:
            fids.append(l['file'])
        for l in end:
            fids.append(l['file'])
    return fids


def fids_in_path(report_data, file_ids_to_remove):
    """
    Skip diagnostic sections and collect file ids in
    report paths for the remaining diagnostic sections.
    """
    all_fids = []

    kept_diagnostics = []

    for diag in report_data['diagnostics']:

        if diag['location']['file'] in file_ids_to_remove:
            continue

        kept_diagnostics.append(diag)

        for pe in diag['path']:
            path_fids = []
            try:
                fids = fids_in_range(pe['ranges'])
                path_fids.extend(fids)
            except KeyError:
                pass

            try:
                fid = pe['location']['file']
                path_fids.append(fid)
            except KeyError:
                pass

            try:
                fids = fids_in_edge(pe['edges'])
                path_fids.extend(fids)
            except KeyError:
                pass

            all_fids.extend(path_fids)

    return all_fids, kept_diagnostics


def remove_report_from_plist(plist_content, skip_handler):
    """
    Parse the original plist content provided by the analyzer
    and return a new plist content where reports were removed
    if they should be skipped.

    WARN !!!!
    If the 'files' array in the plist is modified all of the
    diagnostic section (control, event ...) nodes should be
    re indexed to use the proper file array indexes!!!
    """
    new_data = {}
    try:
        report_data = plistlib.readPlistFromString(plist_content)
    except (ExpatError, TypeError, AttributeError) as ex:
        LOG.error("Failed to parse plist content, "
                  "keeping the original version")
        LOG.error(plist_content)
        LOG.error(ex)
        return plist_content

    file_ids_to_remove = []

    try:
        for i, f in enumerate(report_data['files']):
            if skip_handler.should_skip(f):
                file_ids_to_remove.append(i)

        fids, kept_diagnostics = fids_in_path(report_data, file_ids_to_remove)
        report_data['diagnostics'] = kept_diagnostics

        remove_file = True
        for f in file_ids_to_remove:
            if f in fids:
                remove_file = False
                break

        new_data = report_data
        res = plistlib.writePlistToString(new_data)
        return res

    except KeyError:
        LOG.error("Failed to modify plist content, "
                  "keeping the original version")
        return plist_content


def skip_report_from_plist(plist_file, skip_handler):
    """
    Rewrites the provided plist file where reports
    were removed if they should be skipped.
    """
    with open(plist_file, 'r+') as plist:
        new_plist_content = remove_report_from_plist(plist.read(),
                                                     skip_handler)
        plist.seek(0)
        plist.write(new_plist_content)
        plist.truncate()
