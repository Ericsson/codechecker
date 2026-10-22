# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Reader and writer of the test coverage file of a CodeChecker report
directory.

Coverage converters (e.g. 'report-converter -t lcov') write the coverage of
the source files to '<report dir>/coverage/coverage.json'. 'CodeChecker store'
uploads this file together with the source files it refers to, and the server
stores it in the database. This module is the single place that defines the
location and the format of this file, so the client and the server agree on
it.

Format (version 1):

    {
      "version": 1,
      "tool": "lcov",
      "files": {
        "/abs/path/to/file.c": {
          "covered_lines": [3, 4],
          "uncovered_lines": [5],
          "functions_found": 2,
          "functions_hit": 1
        }
      }
    }
"""

from dataclasses import dataclass, field
import json
import os


# Name of the directory in a report directory which contains the coverage
# file.
COVERAGE_DIR_NAME = 'coverage'

# Name of the coverage file.
COVERAGE_FILE_NAME = 'coverage.json'

COVERAGE_FORMAT_VERSION = 1

# Upper bound of line numbers and counts. The server stores the counts in
# 32-bit integer database columns.
MAX_VALUE = 2**31 - 1


class CoverageFileError(Exception):
    """ Raised when a coverage file is missing or malformed. """


class UnknownCoverageFileError(CoverageFileError):
    """
    Raised when a file is not a CodeChecker test coverage file at all (e.g.
    the 'coverage.json' file of another tool).
    """


@dataclass
class FileCoverage:
    """ Line and function coverage of a single source file. """
    covered_lines: list[int] = field(default_factory=list)
    uncovered_lines: list[int] = field(default_factory=list)
    functions_found: int = 0
    functions_hit: int = 0

    @property
    def lines_found(self) -> int:
        """ Number of executable lines. """
        return len(self.covered_lines) + len(self.uncovered_lines)

    @property
    def lines_hit(self) -> int:
        """ Number of executed lines. """
        return len(self.covered_lines)


def get_coverage_file_path(report_dir: str) -> str:
    """ Returns the path of the coverage file in the given report dir. """
    return os.path.join(report_dir, COVERAGE_DIR_NAME, COVERAGE_FILE_NAME)


def write(
    file_path: str,
    coverage: dict[str, FileCoverage],
    tool: str
):
    """ Write the given coverage data to the given file. """
    files = {}
    for source_path, cov in sorted(coverage.items()):
        files[source_path] = {
            "covered_lines": sorted(cov.covered_lines),
            "uncovered_lines": sorted(cov.uncovered_lines),
            "functions_found": cov.functions_found,
            "functions_hit": cov.functions_hit}

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({"version": COVERAGE_FORMAT_VERSION,
                   "tool": tool,
                   "files": files}, f)


def _is_non_negative_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) \
        and 0 <= value <= MAX_VALUE


def _get_lines(source_path: str, entry: dict, key: str) -> set[int]:
    lines = entry.get(key, [])
    if not isinstance(lines, list) or \
            not all(_is_non_negative_int(line) and line > 0
                    for line in lines):
        raise CoverageFileError(
            f"'{key}' of '{source_path}' must be a list of positive line "
            f"numbers not greater than {MAX_VALUE}.")
    return set(lines)


def _get_count(source_path: str, entry: dict, key: str) -> int:
    value = entry.get(key, 0)
    if not _is_non_negative_int(value):
        raise CoverageFileError(
            f"'{key}' of '{source_path}' must be a non-negative integer "
            f"not greater than {MAX_VALUE}.")
    return value


def parse(data) -> dict[str, FileCoverage]:
    """
    Validate the given decoded coverage file content and return the coverage
    of the source files. Raises CoverageFileError if the data is malformed.
    """
    if not isinstance(data, dict) or "version" not in data:
        raise UnknownCoverageFileError(
            "A JSON object with a 'version' key is expected.")

    version = data.get("version")
    if version != COVERAGE_FORMAT_VERSION:
        raise CoverageFileError(
            f"Unsupported coverage file version: {version!r} (supported: "
            f"{COVERAGE_FORMAT_VERSION}).")

    files = data.get("files")
    if not isinstance(files, dict):
        raise CoverageFileError("'files' must be a JSON object.")

    result: dict[str, FileCoverage] = {}
    for source_path, entry in files.items():
        if not source_path or not isinstance(entry, dict):
            raise CoverageFileError(
                f"Invalid coverage entry of file '{source_path}'.")

        covered = _get_lines(source_path, entry, "covered_lines")

        # A line which was executed is covered, even if another record
        # claimed otherwise.
        uncovered = _get_lines(source_path, entry, "uncovered_lines") \
            - covered

        functions_found = _get_count(source_path, entry, "functions_found")
        functions_hit = _get_count(source_path, entry, "functions_hit")
        if functions_hit > functions_found:
            raise CoverageFileError(
                f"'functions_hit' of '{source_path}' is greater than "
                "'functions_found'.")

        result[source_path] = FileCoverage(
            sorted(covered), sorted(uncovered),
            functions_found, functions_hit)

    return result


def read(file_path: str) -> dict[str, FileCoverage]:
    """
    Read and validate the given coverage file. Raises CoverageFileError if
    the file can not be read or it is malformed.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as err:
        raise CoverageFileError(
            f"Failed to read coverage file '{file_path}': {err}") from err

    try:
        return parse(data)
    except UnknownCoverageFileError as err:
        raise UnknownCoverageFileError(
            f"'{file_path}' is not a CodeChecker test coverage file: "
            f"{err}") from err
    except CoverageFileError as err:
        raise CoverageFileError(
            f"Invalid coverage file '{file_path}': {err}") from err
