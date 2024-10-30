# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import builtins
from dataclasses import dataclass
from datetime import datetime
import itertools
import json
import logging
import os

from typing import Callable, Dict, List, Optional, Protocol, Set, Tuple

from .. import util


LOG = logging.getLogger('report-converter')

FakeChecker: Tuple[str, str] = ("__FAKE__", "__FAKE__")
UnknownChecker: Tuple[str, str] = ("UNKNOWN", "NOT FOUND")


class SkipListHandlers(Protocol):
    should_skip: Callable[[str], bool]


InvalidFileContentMsg: str = \
    "WARNING: source file content is changed or missing. Please re-analyze " \
    "your project to update the reports."


class File:
    def __init__(
        self,
        file_path: str,
        file_id: Optional[str] = None,
        content: Optional[str] = None
    ):
        self.__id = file_path if file_id is None else file_id
        self.__path = file_path
        self.__original_path = file_path
        self.__content = content
        self.__name: Optional[str] = None

    @property
    def id(self) -> str:
        """ Get unique id. """
        return self.__id

    @property
    def path(self) -> str:
        """
        If the 'trim' member function is called it will return the trimmed
        version of the file path otherwise it will return the original
        file path.
        """
        return self.__path

    @property
    def original_path(self) -> str:
        """ Always returns the original file path. """
        return self.__original_path

    @property
    def name(self) -> str:
        """ Returns the file name. """
        if self.__name is None:
            self.__name = os.path.basename(self.__original_path)

        return self.__name

    @property
    def content(self) -> str:
        """ Get file content. """
        if self.__content is None:
            with open(self.original_path, 'r',
                      encoding='utf-8', errors='replace') as f:
                self.__content = f.read()

        return self.__content

    @content.setter
    def content(self, content: str):
        """ Sets the file content manually if it's not set yet. """
        if self.__content is None:
            self.__content = content

    def get_line(self, line: int) -> str:
        """ Get content from the given line.

        Load file content if it's not loaded yet.
        """
        if self.__content is None:
            return util.get_line(self.original_path, line)

        return self.__content.splitlines(keepends=True)[line - 1]

    def trim(self, path_prefixes: Optional[List[str]] = None) -> str:
        """ Removes the longest matching leading path from the file paths. """
        self.__path = util.trim_path_prefixes(
            self.__path, path_prefixes)
        return self.__path

    def to_json(self) -> Dict:
        """ Creates a JSON dictionary. """
        return {
            "id": self.id,
            "path": self.path,
            "original_path": self.original_path}

    def __eq__(self, other) -> bool:
        if isinstance(other, File):
            return self.id == other.id

        if isinstance(other, str):
            return self.id == other

        raise NotImplementedError(
            f"Comparison File object with '{type(other)}' is not supported")

    def __hash__(self) -> int:
        return builtins.hash(self.id)

    def __repr__(self):
        return json.dumps(self.to_json())


def get_or_create_file(
    file_path: str,
    file_cache: Dict[str, File]
) -> File:
    """ Get File object for the given file path. """
    if file_path not in file_cache:
        file_cache[file_path] = File(file_path)

    return file_cache[file_path]


class Range:
    def __init__(
        self,
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int
    ):
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col

    def to_json(self) -> Dict:
        """ Creates a JSON dictionary. """
        return {
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col}

    def __eq__(self, other):
        if isinstance(other, Range):
            return self.start_line == other.start_line and \
                self.start_col == other.start_col and \
                self.end_line == other.end_line and \
                self.end_col == other.end_col

        raise NotImplementedError(
            f"Comparison Range object with '{type(other)}' is not supported")

    def __repr__(self):
        return json.dumps(self.to_json())


class BugPathPosition:
    def __init__(
        self,
        file: File,
        file_range: Optional[Range]
    ):
        self.file = file
        self.range = file_range

    def to_json(self) -> Dict:
        """ Creates a JSON dictionary. """
        return {
            "range": self.range.to_json() if self.range else None,
            "file": self.file.to_json()
        }

    def __eq__(self, other):
        if isinstance(other, BugPathPosition):
            return self.file == other.file and \
                self.range == other.range

        raise NotImplementedError(
            f"Comparison BugPathPosition object with '{type(other)}' is not "
            f"supported")

    def __repr__(self):
        return json.dumps(self.to_json())


class BugPathEvent(BugPathPosition):
    def __init__(
        self,
        message: str,
        file: File,
        line: int,
        column: int,
        file_range: Optional[Range] = None
    ):
        super().__init__(file, file_range)

        # Range can provide more precise location information than line and
        # column. Use that instead of these fields.
        self.line = line
        self.column = column

        self.message = message

    def to_json(self) -> Dict:
        """ Creates a JSON dictionary. """
        return {
            "file": self.file.to_json(),
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "range": self.range.to_json() if self.range else None
        }

    def __eq__(self, other):
        if isinstance(other, BugPathEvent):
            return self.file == other.file and \
                self.line == other.line and \
                self.column == other.column and \
                self.message == other.message and \
                self.range == other.range

        raise NotImplementedError(
            f"Comparison BugPathEvent object with '{type(other)}' is not "
            f"supported")

    def __repr__(self):
        return json.dumps(self.to_json())


class MacroExpansion(BugPathEvent):
    def __init__(
        self,
        message: str,  # Expanded message.
        name: str,  # Macro name which will be expanded.
        file: File,
        line: int,
        column: int,
        file_range: Optional[Range] = None
    ):
        super().__init__(message, file, line, column, file_range)
        self.name = name

    def to_json(self) -> Dict:
        """ Creates a JSON dictionary. """
        return {
            "name": self.name,
            **super().to_json()
        }

    def __repr__(self):
        return json.dumps(self.to_json())


@dataclass
class SourceReviewStatus:
    """
    Helper class for handling in source review statuses.
    Collect the same info as a review status rule.

    TODO: rename this class, because this not only represents review statuses
          in source code comments but in review status yaml too.
    """
    status: str = "unreviewed"
    message: bytes = b""
    bug_hash: str = ""
    in_source: bool = False
    author: Optional[str] = None
    date: Optional[datetime] = None

    def formatted_status(self):
        return self.status.lower().replace('_', ' ').capitalize()


class Report:
    """ Represents a report object. """

    def __init__(
        self,
        file: File,
        line: int,
        column: int,
        message: str,
        checker_name: str,
        severity: Optional[str] = None,
        report_hash: Optional[str] = None,
        report_super_hash: Optional[str] = None,
        analyzer_name: Optional[str] = None,
        category: Optional[str] = None,
        type: Optional[str] = None,  # pylint: disable=redefined-builtin
        analyzer_result_file_path: Optional[str] = None,
        source_line: Optional[str] = None,
        bug_path_events: Optional[List[BugPathEvent]] = None,
        bug_path_positions: Optional[List[BugPathPosition]] = None,
        notes: Optional[List[BugPathEvent]] = None,
        macro_expansions: Optional[List[MacroExpansion]] = None,
        annotations: Optional[Dict[str, str]] = None,
        static_message: Optional[str] = None,
        review_status: Optional[SourceReviewStatus] = SourceReviewStatus()
    ):
        """
        This constructor populates the members of the Report object.

        static_message: hash.get_report_hash() function generates a hash value
            based on this report object. The checker message is usually the
            part of this hash. However, sometimes a checker message may contain
            dynamically generated parts (e.g. sanitizers include some memory
            addresses). This results changing hashes at every analysis
            execution. In this case the report converter of that analyzer may
            provide a more stable message which is used only for hash
            generation.
        """
        self.analyzer_result_file_path = analyzer_result_file_path
        self.file = file
        self.line = line
        self.column = column
        self.message = message
        self.checker_name = checker_name
        self.severity = severity
        self.report_hash = report_super_hash
        self.report_hash = report_hash
        self.analyzer_name = analyzer_name
        self.category = category  # TODO: Remove this. DEPRECATED.
        self.type = type  # TODO: Remove this. DEPRECATED.
        self.annotations = annotations

        self.static_message = \
            message if static_message is None else static_message

        self.bug_path_events = bug_path_events \
            if bug_path_events is not None else \
            [BugPathEvent(self.message, self.file, self.line, self.column)]

        self.bug_path_positions = bug_path_positions \
            if bug_path_positions is not None else []
        self.notes = notes if notes is not None else []
        self.macro_expansions = macro_expansions \
            if macro_expansions is not None else []

        self.review_status = review_status

        self.__source_line: Optional[str] = source_line
        self.__files: Optional[Set[File]] = None
        self.__changed_files: Optional[Set[str]] = None

    @property
    def source_line(self) -> str:
        """ Get the source line for the main location.

        If the source line is already set returns that
        if not tries to read it from the disk.
        """
        if not self.__source_line:
            if self.file.original_path in self.changed_files:
                self.__source_line = InvalidFileContentMsg
            else:
                self.__source_line = self.file.get_line(self.line)

        return self.__source_line

    @source_line.setter
    def source_line(self, source_line):
        """ Sets the source line manually if it's not set yet. """
        if self.__source_line is None:
            self.__source_line = source_line

    def trim_path_prefixes(self, path_prefixes: Optional[List[str]] = None):
        """ Removes the longest matching leading path from the file paths. """
        self.file.trim(path_prefixes)

        for event in itertools.chain(
            self.bug_path_events,
            self.bug_path_positions,
            self.notes,
            self.macro_expansions
        ):
            event.file.trim(path_prefixes)

    @property
    def files(self) -> Set[File]:
        """ Returns all referenced file paths. """
        if self.__files is not None:
            return self.__files

        self.__files = {self.file}

        for event in itertools.chain(
            self.bug_path_events,
            self.bug_path_positions,
            self.notes,
            self.macro_expansions
        ):
            self.__files.add(event.file)

        return self.__files

    @property
    def trimmed_files(self) -> Set[str]:
        """ Returns all referenced trimmed file paths. """
        return {file.path for file in self.files}

    @property
    def original_files(self) -> Set[str]:
        """ Returns all referenced original file paths. """
        return {file.original_path for file in self.files}

    @property
    def changed_files(self) -> Set[str]:
        """
        Returns set of files which are changed or not available compared to the
        analyzer result file.
        """
        if self.__changed_files is not None:
            return self.__changed_files

        self.__changed_files = set()

        if self.analyzer_result_file_path is None:
            LOG.warning("No analyzer result file path is set for report: %s",
                        self)
            return self.__changed_files

        analyzer_result_file_mtime = util.get_last_mod_time(
            self.analyzer_result_file_path)

        if analyzer_result_file_mtime is None:
            # Failed to get the modification time for a file mark it as
            # changed.
            self.__changed_files.add(self.analyzer_result_file_path)

        for file_path in self.original_files:
            if not os.path.exists(file_path):
                self.__changed_files.add(file_path)
                continue

            f_mtime = util.get_last_mod_time(file_path)

            if not f_mtime:
                self.__changed_files.add(file_path)
                continue

            if not analyzer_result_file_mtime or \
                    f_mtime > analyzer_result_file_mtime:
                self.__changed_files.add(file_path)

        return self.__changed_files

    @changed_files.setter
    def changed_files(self, changed_files: Set[str]):
        """ Sets the changed files list manually if it's not set yet. """
        if self.__changed_files is None:
            self.__changed_files = changed_files

    def skip(self, skip_handlers: Optional[SkipListHandlers]) -> bool:
        """ True if the report should be skipped. """
        if not skip_handlers:
            return False

        return skip_handlers.should_skip(self.file.original_path)

    def to_json(self) -> Dict:
        """ Creates a JSON dictionary. """
        return {
            "analyzer_result_file_path": self.analyzer_result_file_path,
            "file": self.file.to_json(),
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "checker_name": self.checker_name,
            "severity": self.severity,
            "report_hash": self.report_hash,
            "analyzer_name": self.analyzer_name,
            # DEPRECATED: 'category' is deprecated in 6.24.0, as it is not
            # parsed, understood, or handled by the report server.
            # It should be removed!
            "category": self.category,
            # DEPRECATED: 'type' is deprecated in 6.24.0, as it is not
            # parsed, understood, or handled by the report server.
            # It should be removed!
            "type": self.type,
            "review_status": self.review_status.status
            if self.review_status else '',
            "bug_path_events": [e.to_json() for e in self.bug_path_events],
            "bug_path_positions": [
                p.to_json() for p in self.bug_path_positions],
            "notes": [n.to_json() for n in self.notes],
            "macro_expansions": [m.to_json() for m in self.macro_expansions]
        }

    def __eq__(self, other):
        if isinstance(other, Report):
            return self.file == other.file and \
                self.line == other.line and \
                self.column == other.column and \
                self.message == other.message and \
                self.checker_name == other.checker_name and \
                self.report_hash == other.report_hash

        raise NotImplementedError(
            f"Comparison Range object with '{type(other)}' is not supported")

    def __hash__(self):
        """
        We consider two report objects equivalent if these members are the
        same. This way a report object can be used as key in a dict.
        WARNING! Make sure that the same members are compared by __eq__().
        """
        return builtins.hash((
            self.file,
            self.line,
            self.column,
            self.message,
            self.checker_name,
            self.report_hash))

    def __repr__(self):
        return json.dumps(self.to_json())
