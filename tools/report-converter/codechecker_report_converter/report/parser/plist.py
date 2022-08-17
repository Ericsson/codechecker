# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Parse the plist output of an analyzer
"""

import importlib
import logging
import os
import plistlib
import traceback
import sys

from plistlib import _PlistParser  # type: ignore
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

from xml.parsers.expat import ExpatError

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from mypy_extensions import TypedDict

from codechecker_report_converter import __title__, __version__
from codechecker_report_converter.report import BugPathEvent, \
    BugPathPosition, File, get_or_create_file, MacroExpansion, Range, Report
from codechecker_report_converter.report.hash import get_report_hash, HashType
from codechecker_report_converter.report.parser.base import AnalyzerInfo, \
    BaseParser
from codechecker_report_converter.util import load_json_or_empty


LOG = logging.getLogger('report-converter')


EXTENSION = 'plist'

PlistItem = Any


class _LXMLPlistEventHandler:
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


class _LXMLPlistParser(_PlistParser):
    """
    Plist parser which uses the lxml library to parse XML data.

    The benefit of this library that this is faster than other libraries so it
    will improve the performance of the plist parsing.
    """
    def __init__(self, dict_type=dict):
        # Since Python 3.9 plistlib._PlistParser.__init__ has changed:
        # https://github.com/python/cpython/commit/ce81a925ef
        # To be backward compatible with old interpreters we need to call this
        # function based on conditions:
        params = _PlistParser.__init__.__code__.co_varnames
        if len(params) == 3 and "use_builtin_types" in params:
            # Before 3.9 interpreter.
            _PlistParser.__init__(self, True, dict_type)
        else:
            _PlistParser.__init__(self, dict_type)  # pylint: disable=E1120

        self.event_handler = _LXMLPlistEventHandler()
        self.event_handler.start = self.handle_begin_element
        self.event_handler.end = self.handle_end_element
        self.event_handler.data = self.handle_data

        from lxml.etree import XMLParser  # pylint: disable=no-name-in-module
        self.parser = XMLParser(target=self.event_handler)

    def parse(self, fileobj):
        # pylint: disable=no-name-in-module
        from lxml.etree import parse, XMLSyntaxError

        try:
            parse(fileobj, self.parser)
        except XMLSyntaxError as ex:
            LOG.error("Invalid plist file '%s': %s", fileobj.name, ex)
            return

        return self.root


class DiagLoc(TypedDict):
    line: int
    col: int


class DiagEdge(TypedDict):
    start: Tuple[DiagLoc, DiagLoc]
    end: Tuple[DiagLoc, DiagLoc]


class DiagPath(TypedDict):
    kind: str
    message: str
    location: DiagLoc
    edges: List[DiagEdge]


def is_same_control_item(
    curr: DiagPath,
    prev: DiagPath
) -> bool:
    """ True if the given diag paths are same. """
    curr_start_range_begin = curr['edges'][0]['start'][0]
    curr_start_range_end = curr['edges'][0]['start'][1]

    prev_end_range_begin = prev['edges'][0]['end'][0]
    prev_end_range_end = prev['edges'][0]['end'][1]

    return curr_start_range_begin == prev_end_range_begin and \
        curr_start_range_end == prev_end_range_end


def parse(fp: BinaryIO):
    """
    Read a .plist file. Return the unpacked root object (which usually is a
    dictionary).

    Use 'lxml' library to read the given plist file if it is available,
    otherwise use 'plistlib' library.
    """
    try:
        importlib.import_module('lxml')
        parser = _LXMLPlistParser()
        return parser.parse(fp)
    except (ExpatError, TypeError, AttributeError) as err:
        LOG.warning('Invalid plist file')
        LOG.warning(err)
        return
    except ImportError:
        LOG.debug("lxml library is not available. Use plistlib to parse plist "
                  "files.")

    try:
        return plistlib.load(fp)
    except (ExpatError, TypeError, AttributeError, ValueError,
            plistlib.InvalidFileException) as err:
        LOG.warning('Invalid plist file')
        LOG.warning(err)
        return


def get_file_index_map(
    plist: Any,
    source_dir_path: str,
    file_cache: Dict[str, File]
) -> Dict[int, File]:
    """ Get file index map from the given plist object. """
    file_index_map: Dict[int, File] = {}

    for i, orig_file_path in enumerate(plist.get('files', [])):
        file_path = os.path.normpath(os.path.join(
            source_dir_path, orig_file_path))
        file_index_map[i] = get_or_create_file(file_path, file_cache)

    return file_index_map


class Parser(BaseParser):
    def get_reports(
        self,
        analyzer_result_file_path: str,
        source_dir_path: Optional[str] = None
    ) -> List[Report]:
        """ Get reports from the given analyzer result file. """
        reports: List[Report] = []

        if not source_dir_path:
            source_dir_path = os.path.dirname(analyzer_result_file_path)

        try:
            with open(analyzer_result_file_path, 'rb') as fp:
                plist = parse(fp)

            if not plist:
                return reports

            metadata = plist.get('metadata')

            files = get_file_index_map(
                plist, source_dir_path, self._file_cache)

            for diag in plist.get('diagnostics', []):
                report = self.__create_report(
                    analyzer_result_file_path, diag, files, metadata)

                if report.report_hash is None:
                    report.report_hash = get_report_hash(
                        report, HashType.PATH_SENSITIVE)

                reports.append(report)
        except KeyError as ex:
            LOG.warning("Failed to get file path id! Found files: %s. "
                        "KeyError: %s", files, ex)
        except IndexError as iex:
            LOG.warning("Indexing error during processing plist file %s",
                        analyzer_result_file_path)
            LOG.warning(type(iex))
            LOG.warning(repr(iex))
            _, _, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
        except Exception as ex:
            LOG.warning("Error during processing reports from the plist "
                        "file: %s", analyzer_result_file_path)
            traceback.print_exc()
            LOG.warning(type(ex))
            LOG.warning(ex)
        finally:
            return reports

    def __create_report(
        self,
        analyzer_result_file_path: str,
        diag: Dict,
        files: Dict[int, File],
        metadata: Dict[str, Any]
    ) -> Report:
        location = diag.get('location', {})
        checker_name = diag.get('check_name', "unknown")
        analyzer_name = self.__get_analyzer_name(checker_name, metadata)
        severity = self.get_severity(checker_name)

        return Report(
            analyzer_result_file_path=analyzer_result_file_path,
            file=files[location['file']],
            line=location.get('line', -1),
            column=location.get('col', -1),
            message=diag.get('description', ''),
            checker_name=checker_name,
            severity=severity,
            report_hash=diag.get('issue_hash_content_of_line_in_context'),
            analyzer_name=analyzer_name,
            category=diag.get('category'),
            source_line=None,
            bug_path_events=self.__get_bug_path_events(diag, files),
            bug_path_positions=self.__get_bug_path_positions(diag, files),
            notes=self.__get_notes(diag, files),
            macro_expansions=self.__get_macro_expansions(diag, files))

    def __get_analyzer_name(
        self,
        checker_name: str,
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """ Get analyzer name for the given checker name. """
        if metadata:
            name = metadata.get("analyzer", {}).get("name")
            if name:
                return name

        if checker_name.startswith('clang-diagnostic-'):
            return 'clang-tidy'

        return None

    def __get_bug_event_locations(self, item: PlistItem):
        """ Get bug path position for the given plist item. """
        location = item['location']
        ranges = item.get("ranges")

        # Range can provide more precise location information.
        # Use that if available.
        if ranges:
            return location, ranges[0][0], ranges[0][1]

        return location, location, location

    def __get_bug_path_events(
        self,
        diag,
        files: Dict[int, File]
    ) -> List[BugPathEvent]:
        """ Get bug path events. """
        events = []

        for item in diag.get('path', []):
            if item.get('kind') != 'event':
                continue

            location, start_loc, end_loc = self.__get_bug_event_locations(item)
            events.append(BugPathEvent(
                message=item['message'],
                file=files[location['file']],
                line=location['line'],
                column=location['col'],
                range=Range(
                    start_loc['line'], start_loc['col'],
                    end_loc['line'], end_loc['col'])))

        return events

    def __get_bug_path_positions(
        self,
        diag,
        files: Dict[int, File]
    ) -> List[BugPathPosition]:
        """ Get bug path positions.

        In plist file the source and target of the arrows are provided as
        starting and ending ranges of the arrow. The path A->B->C is given as
        A->B and B->C, thus range B is provided twice if multiple control event
        kinds are followed each other. So in the loop we will not store the
        start point if the previous path event was a control event.
        """
        bug_path_positions = []

        prev_control_item = None
        for item in diag.get('path', []):
            if item.get('kind') != 'control':
                continue

            try:
                edges = item['edges'][0]

                edge = None
                if prev_control_item:
                    if not is_same_control_item(item, prev_control_item):
                        edge = edges['start']
                else:
                    edge = edges['start']

                if edge:
                    bug_path_positions.append(BugPathPosition(
                        file=files[edge[1]['file']],
                        range=Range(
                            edge[0]['line'], edge[0]['col'],
                            edge[1]['line'], edge[1]['col'])))

                bug_path_positions.append(BugPathPosition(
                    file=files[edges['end'][1]['file']],
                    range=Range(
                        edges['end'][0]['line'], edges['end'][0]['col'],
                        edges['end'][1]['line'], edges['end'][1]['col'])))

                prev_control_item = item
            except IndexError:
                # Edges might be empty nothing can be stored.
                continue

        return bug_path_positions

    def __get_notes(
        self,
        diag,
        files: Dict[int, File]
    ) -> List[BugPathEvent]:
        """ Get notes. """
        notes = []

        for note in diag.get('notes', []):
            if not note['message']:
                continue

            location, start_loc, end_loc = self.__get_bug_event_locations(note)
            notes.append(BugPathEvent(
                message=note['message'],
                file=files[location['file']],
                line=location['line'],
                column=location['col'],
                range=Range(
                    start_loc['line'], start_loc['col'],
                    end_loc['line'], end_loc['col'])))

        return notes

    def __get_macro_expansions(
        self,
        diag,
        files: Dict[int, File]
    ) -> List[MacroExpansion]:
        """ Get macro expansion. """
        macro_expansions = []

        for macro in diag.get('macro_expansions', []):
            if not macro['expansion']:
                continue

            location, start_loc, end_loc = self.__get_bug_event_locations(
                macro)
            macro_expansions.append(MacroExpansion(
                message=macro['expansion'],
                name=macro['name'],
                file=files[location['file']],
                line=location['line'],
                column=location['col'],
                range=Range(
                    start_loc['line'], start_loc['col'],
                    end_loc['line'], end_loc['col'])))

        return macro_expansions

    def __get_tool_info(self) -> Tuple[str, str]:
        """ Get tool info.

        If this was called through CodeChecker, this function will return
        CodeChecker information, otherwise this tool (report-converter)
        information.
        """
        data_files_dir_path = os.environ.get('CC_DATA_FILES_DIR')
        if data_files_dir_path:
            analyzer_version_file_path = os.path.join(
                data_files_dir_path, 'config', 'analyzer_version.json')
            if os.path.exists(analyzer_version_file_path):
                data = load_json_or_empty(analyzer_version_file_path, {})
                version = data.get('version')
                if version:
                    return 'CodeChecker', f"{version['major']}." \
                        f"{version['minor']}.{version['revision']}"

        return __title__, __version__

    def convert(
        self,
        reports: List[Report],
        analyzer_info: Optional[AnalyzerInfo] = None
    ):
        """ Converts the given reports. """
        tool_name, tool_version = self.__get_tool_info()

        data: Dict[str, Any] = {
            'files': [],
            'diagnostics': [],
            'metadata': {
                'generated_by': {
                    'name': tool_name,
                    'version': tool_version
                }
            }
        }

        if analyzer_info:
            data['metadata']['analyzer'] = {'name': analyzer_info.name}

        files = set()
        for report in reports:
            files.update(report.original_files)

        file_index_map: Dict[str, int] = {}
        for idx, file_path in enumerate(sorted(files)):
            data['files'].append(file_path)
            file_index_map[file_path] = idx

        for report in reports:
            diagnostic = {
                'location': self._create_location(
                    report.line, report.column,
                    file_index_map[report.file.original_path]),
                'issue_hash_content_of_line_in_context': report.report_hash,
                'check_name': report.checker_name,
                'description': report.message,
                'category': report.category or 'unknown'
            }

            if report.analyzer_name:
                diagnostic['type'] = report.analyzer_name

            path = []
            if report.bug_path_positions:
                for i in range(len(report.bug_path_positions) - 1):
                    start = report.bug_path_positions[i]
                    end = report.bug_path_positions[i + 1]
                    if start.range and end.range:
                        edge = self._create_control_edge(
                            start.range, start.file,
                            end.range, end.file,
                            file_index_map)
                        path.append(self._create_control_edges([edge]))
            elif len(report.bug_path_events) > 1:
                # Create bug path positions from bug path events.
                for i in range(len(report.bug_path_events) - 1):
                    start = report.bug_path_events[i]
                    start_range = self._get_bug_path_event_range(start)

                    end = report.bug_path_events[i + 1]
                    end_range = self._get_bug_path_event_range(end)

                    if start_range == end_range:
                        continue

                    edge = self._create_control_edge(
                        start_range, start.file,
                        end_range, end.file,
                        file_index_map)
                    path.append(self._create_control_edges([edge]))

            # Add bug path events after control points.
            if report.bug_path_events:
                for event in report.bug_path_events:
                    path.append(self._create_event(event, file_index_map))

            diagnostic['path'] = path

            if report.notes:
                diagnostic['notes'] = []
                for note in report.notes:
                    diagnostic['notes'].append(
                        self._create_note(note, file_index_map))

            if report.macro_expansions:
                diagnostic['macro_expansions'] = []
                for macro_expansion in report.macro_expansions:
                    diagnostic['macro_expansions'].append(
                        self._create_macro_expansion(
                            macro_expansion, file_index_map))

            data['diagnostics'].append(diagnostic)

        return data

    def write(self, data: Any, output_file_path: str):
        """ Creates an analyzer output file from the given data. """
        try:
            with open(output_file_path, 'wb') as f:
                plistlib.dump(data, f)
        except TypeError as err:
            LOG.error('Failed to write plist file: %s', output_file_path)
            LOG.error(err)
            import traceback
            traceback.print_exc()

    def _get_bug_path_event_range(self, event: BugPathEvent) -> Range:
        """ Get range for bug path event. """
        if event.range:
            return event.range

        return Range(event.line, event.column, event.line, event.column)

    def _create_location(
        self,
        line: int,
        column: int,
        file_index: int
    ):
        """ Create a location section from the message. """
        return {'line': line, 'col': column, 'file': file_index}

    def _create_event(
        self,
        event: BugPathEvent,
        file_index_map: Dict[str, int]
    ):
        """ Create an event. """
        data = {
            'kind': 'event',
            'location': self._create_location(
                event.line, event.column,
                file_index_map[event.file.original_path]),
            'depth': 0,
            'message': event.message}

        if event.range:
            data['ranges'] = [self._create_range(
                event.range, file_index_map[event.file.original_path])]

        return data

    def _create_control_edges(self, edges: List[Dict]) -> Dict:
        """ """
        return {'kind': 'control', 'edges': edges}

    def _create_control_edge(
        self,
        start_range: Range,
        start_file: File,
        end_range: Range,
        end_file: File,
        file_index_map: Dict[str, int]
    ) -> Dict:
        """ Creates a control point. """
        return {
            'start': self._create_range(
                start_range, file_index_map[start_file.original_path]),
            'end': self._create_range(
                end_range, file_index_map[end_file.original_path])}

    def _create_note(
        self,
        note: BugPathEvent,
        file_index_map: Dict[str, int]
    ):
        """ Creates a note. """
        data = {
            'location': self._create_location(
                note.line, note.column,
                file_index_map[note.file.original_path]),
            'message': note.message}

        if note.range:
            data['ranges'] = [self._create_range(
                note.range, file_index_map[note.file.original_path])]

        return data

    def _create_range(
        self,
        range: Range,
        file_idx: int
    ) -> List:
        """ Creates a range. """
        return [
            self._create_location(range.start_line, range.start_col, file_idx),
            self._create_location(range.end_line, range.end_col, file_idx)]

    def _create_macro_expansion(
        self,
        macro_expansion: MacroExpansion,
        file_index_map: Dict[str, int]
    ):
        """ Creates a macro expansion. """
        return {
            'name': macro_expansion.name,
            'expansion': macro_expansion.message,
            'location': self._create_location(
                macro_expansion.line, macro_expansion.column,
                file_index_map[macro_expansion.file.original_path])}

    def replace_report_hash(
        self,
        plist_file_path: str,
        hash_type=HashType.CONTEXT_FREE
    ):
        """
        Override hash in the given file by using the given version hash.
        """
        try:
            with open(plist_file_path, 'rb+') as f:
                plist = plistlib.load(f)
                f.seek(0)
                f.truncate()

                metadata = plist.get('metadata')
                analyzer_result_dir_path = os.path.dirname(plist_file_path)

                file_cache: Dict[str, File] = {}
                files = get_file_index_map(
                    plist, analyzer_result_dir_path, file_cache)

                for diag in plist['diagnostics']:
                    report = self.__create_report(
                        plist_file_path, diag, files, metadata)
                    diag['issue_hash_content_of_line_in_context'] = \
                        get_report_hash(report, hash_type)

                plistlib.dump(plist, f)
        except (TypeError, AttributeError,
                plistlib.InvalidFileException) as err:
            LOG.warning('Failed to process plist file: %s wrong file format?',
                        plist_file_path)
            LOG.warning(err)
        except IndexError as iex:
            LOG.warning('Indexing error during processing plist file %s',
                        plist_file_path)
            LOG.warning(type(iex))
            LOG.warning(repr(iex))
            _, _, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
        except Exception as ex:
            LOG.warning('Error during processing reports from the plist '
                        'file: %s', plist_file_path)
            traceback.print_exc()
            LOG.warning(type(ex))
            LOG.warning(ex)
