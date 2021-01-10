# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
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
import importlib
import os
import sys
import traceback
import plistlib
import portalocker
from typing import List, Dict, Union, Tuple
from xml.parsers.expat import ExpatError

from codechecker_common.logger import get_logger
from codechecker_common.report import Report
from codechecker_report_hash.hash import get_report_hash, HashType

LOG = get_logger('report')


class LXMLPlistEventHandler(object):
    """
    Basic lxml event handler.
    """
    def start(self, tag, attrib):
        pass

    def end(self, tag):
        pass

    def data(self, data):
        pass

    def comment(self, text):
        pass

    def close(self):
        return "closed!"


class LXMLPlistParser(plistlib._PlistParser):
    """
    Plist parser which uses the lxml library to parse XML data.

    The benefit of this library that this is faster than other libraries so it
    will improve the performance of the plist parsing.
    """
    def __init__(self, use_builtin_types=True, dict_type=dict):
        plistlib._PlistParser.__init__(self, use_builtin_types, dict_type)

        self.event_handler = LXMLPlistEventHandler()
        self.event_handler.start = self.handle_begin_element
        self.event_handler.end = self.handle_end_element
        self.event_handler.data = self.handle_data

        from lxml.etree import XMLParser
        self.parser = XMLParser(target=self.event_handler)

    def parse(self, fileobj):
        from lxml.etree import parse, XMLSyntaxError

        try:
            parse(fileobj, self.parser)
        except XMLSyntaxError as ex:
            LOG.error("Invalid plist file '%s': %s", fileobj.name, ex)
            return

        return self.root


def parse_plist(plist_file_obj):
    """
    Read a .plist file. Return the unpacked root object (which usually is a
    dictionary).

    Use 'lxml' library to read the given plist file if it is available,
    otherwise use 'plistlib' library.
    """
    try:
        importlib.import_module('lxml')
        parser = LXMLPlistParser()
        return parser.parse(plist_file_obj)
    except (ExpatError, TypeError, AttributeError) as err:
        LOG.warning('Invalid plist file')
        LOG.warning(err)
        return
    except ImportError:
        LOG.debug("lxml library is not available. Use plistlib to parse plist "
                  "files.")

    try:
        return plistlib.load(plist_file_obj)
    except (ExpatError, TypeError, AttributeError, ValueError,
            plistlib.InvalidFileException) as err:
        LOG.warning('Invalid plist file')
        LOG.warning(err)
        return


def get_checker_name(diagnostic, path=""):
    """
    Check if checker name is available in the report.
    Checker name was not available in older clang versions before 3.7.
    """
    checker_name = diagnostic.get('check_name')
    if not checker_name:
        LOG.warning("Check name wasn't found in the plist file '%s'. ", path)
        checker_name = "unknown"
    return checker_name


def parse_plist_file(path: str,
                     source_root: Union[str, None] = None,
                     allow_plist_update=True) \
                             -> Tuple[Dict[int, str], List[Report]]:
    """
    Parse the reports from a plist file.
    One plist file can contain multiple reports.
    """
    LOG.debug("Parsing plist: %s", path)

    reports = []
    source_files = {}

    try:
        plist = None
        with open(path, 'rb') as plist_file_obj:
            plist = parse_plist(plist_file_obj)

        if not plist:
            LOG.error("Failed to parse plist %s", path)
            return {}, []

        metadata = plist.get('metadata')

        mentioned_files = plist.get('files', [])

        # file index to filepath that bugpath events refer to
        source_files = \
            {i: filepath for i, filepath in enumerate(mentioned_files)}
        diag_changed = False
        for diag in plist.get('diagnostics', []):

            available_keys = list(diag.keys())

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
            file_path = mentioned_files[diag['location']['file']]
            if source_root:
                file_path = os.path.join(source_root, file_path.lstrip('/'))
            main_section['location']['file'] = file_path
            report_hash = diag.get('issue_hash_content_of_line_in_context')

            if not report_hash:
                # Generate hash value if it is missing from the report.
                report_hash = get_report_hash(diag, file_path,
                                              HashType.PATH_SENSITIVE)

                main_section['issue_hash_content_of_line_in_context'] = \
                    report_hash

            if 'issue_hash_content_of_line_in_context' not in diag:
                # If the report hash was not in the plist, we set it in the
                # diagnostic section for later update.
                diag['issue_hash_content_of_line_in_context'] = report_hash
                diag_changed = True

            bug_path_items = [item for item in diag['path']]
            reports.append(Report(main_section,
                                  bug_path_items,
                                  source_files,
                                  metadata))

        if diag_changed and allow_plist_update:
            # If the diagnostic section has changed we update the plist file.
            # This way the client will always send a plist file where the
            # report hash field is filled.
            plistlib.dump(plist, path)
    except IndexError as iex:
        LOG.warning('Indexing error during processing plist file %s', path)
        LOG.warning(type(iex))
        LOG.warning(repr(iex))
        _, _, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    except Exception as ex:
        LOG.warning('Error during processing reports from the plist file: %s',
                    path)
        traceback.print_exc()
        LOG.warning(type(ex))
        LOG.warning(ex)
    finally:
        return source_files, reports


def fids_in_range(rng):
    """
    Get the file ids from a range.
    """
    fids = []
    for r in rng:
        for line in r:
            fids.append(line['file'])
    return fids


def fids_in_edge(edges):
    """
    Get the file ids from an edge.
    """
    fids = []
    for e in edges:
        start = e['start']
        end = e['end']
        for line in start:
            fids.append(line['file'])
        for line in end:
            fids.append(line['file'])
    return fids


def transform_diag_element(element, file_ids_to_remove, new_file_ids):
    """
    This function will update every file attribute of the given diagnostic
    element.
    On the first call it will get a diagnostic section dictionary and
    recursively traverse all children of it. If the child element is a file
    attribute it will update it by using the 'new_file_ids' dictionary.

    It will return False if one of the file attribute is in the removable file
    list. Otherwise it will return True.
    """
    if isinstance(element, dict):
        for k, v in element.items():
            if k == 'file':
                if v in file_ids_to_remove:
                    return False
                else:
                    element['file'] = new_file_ids[v]
            else:
                if not transform_diag_element(v, file_ids_to_remove,
                                              new_file_ids):
                    return False
    elif isinstance(element, list) or isinstance(element, tuple):
        for v in element:
            if not transform_diag_element(v, file_ids_to_remove, new_file_ids):
                return False

    return True


def get_kept_report_data(report_data, file_ids_to_remove):
    """
    This function will iterate over the diagnostic section of the given
    report data and returns the list of diagnostics and files which should
    be kept.
    """
    kept_files = []
    new_file_ids = {}
    all_files = report_data['files']
    for idx, file in enumerate(all_files):
        if idx not in file_ids_to_remove:
            new_file_ids[idx] = len(kept_files)
            kept_files.append(file)

    kept_diagnostics = []
    for diag in report_data['diagnostics']:
        if transform_diag_element(diag, file_ids_to_remove, new_file_ids):
            kept_diagnostics.append(diag)

    return kept_diagnostics, kept_files


def remove_report_from_plist(plist_file_obj, skip_handler):
    """
    Parse the original plist content provided by the analyzer
    and return a new plist content where reports were removed
    if they should be skipped. If the remove failed for some reason None
    will be returned.

    WARN !!!!
    If the 'files' array in the plist is modified all of the
    diagnostic section (control, event ...) nodes should be
    re indexed to use the proper file array indexes!!!
    """
    report_data = None
    try:
        report_data = parse_plist(plist_file_obj)
        if not report_data:
            return
    except Exception as ex:
        LOG.error("Plist parsing error")
        LOG.error(ex)
        return

    file_ids_to_remove = []

    try:
        for i, f in enumerate(report_data['files']):
            if skip_handler.should_skip(f):
                file_ids_to_remove.append(i)

        kept_diagnostics, kept_files = get_kept_report_data(report_data,
                                                            file_ids_to_remove)
        report_data['diagnostics'] = kept_diagnostics
        report_data['files'] = kept_files if kept_diagnostics else []

        return plistlib.dumps(report_data)

    except KeyError:
        LOG.error("Failed to modify plist content, "
                  "keeping the original version")
        return


def skip_report_from_plist(plist_file, skip_handler):
    """
    Rewrites the provided plist file where reports
    were removed if they should be skipped.
    """
    new_plist_content = None

    with portalocker.Lock(plist_file, 'rb+') as plist_f:
        new_plist_content = remove_report_from_plist(plist_f, skip_handler)

        if new_plist_content:
            plist_f.seek(0)
            plist_f.truncate()
            plist_f.write(new_plist_content)

            plist_f.flush()
            os.fsync(plist_f.fileno())
        else:
            LOG.error("Failed to skip report from the plist file: %s",
                      plist_file)
