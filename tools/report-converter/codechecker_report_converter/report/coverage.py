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
          "functions_hit": 1,
          "branches_found": 4,
          "branches_hit": 3,
          "mcdc_found": 4,
          "mcdc_hit": 1,
          "regions_found": 6,
          "regions_hit": 5,
          "line_branches": [[4, 3, 4]],
          "line_mcdc": [[4, 1, 4, ["C1 true", "C2 false"]]],
          "uncovered_regions": [[5, 3, 5, 11]]
        }
      }
    }

All keys of a file entry are optional. The branch, MC/DC and region keys
were added later, so a missing key means that the metric was not measured
(e.g. LCOV tracefiles have no region coverage):

- 'line_branches': [line, hit, found] per line with branches.
- 'line_mcdc': [line, hit, found, [labels of the uncovered conditions]] per
  line with MC/DC conditions.
- 'uncovered_regions': [start line, start column, end line, end column]
  of the code regions which were never executed. Lines and columns are
  1-based, the end column is exclusive.
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


# Maximum number of uncovered condition labels of a line and the maximum
# length of a label.
MAX_LABELS = 64
MAX_LABEL_LENGTH = 256

# Names of the (found, hit) count pairs of the optional metrics.
COUNT_KEYS = (('branches_found', 'branches_hit'),
              ('mcdc_found', 'mcdc_hit'),
              ('regions_found', 'regions_hit'))


@dataclass
class FileCoverage:
    """ Test coverage of a single source file. """
    covered_lines: list[int] = field(default_factory=list)
    uncovered_lines: list[int] = field(default_factory=list)
    functions_found: int = 0
    functions_hit: int = 0
    branches_found: int = 0
    branches_hit: int = 0
    mcdc_found: int = 0
    mcdc_hit: int = 0
    regions_found: int = 0
    regions_hit: int = 0

    # [line, hit, found] of the lines with branches.
    line_branches: list[list[int]] = field(default_factory=list)

    # [line, hit, found, [uncovered condition labels]] of the lines with
    # MC/DC conditions.
    line_mcdc: list[list] = field(default_factory=list)

    # [start line, start column, end line, end column] of the code regions
    # which were never executed.
    uncovered_regions: list[list[int]] = field(default_factory=list)

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
        entry = {
            "covered_lines": sorted(cov.covered_lines),
            "uncovered_lines": sorted(cov.uncovered_lines),
            "functions_found": cov.functions_found,
            "functions_hit": cov.functions_hit}

        # The optional metrics are written only if they were measured.
        for found_key, hit_key in COUNT_KEYS:
            if getattr(cov, found_key):
                entry[found_key] = getattr(cov, found_key)
                entry[hit_key] = getattr(cov, hit_key)

        if cov.line_branches:
            entry["line_branches"] = sorted(cov.line_branches)
        if cov.line_mcdc:
            entry["line_mcdc"] = sorted(cov.line_mcdc)
        if cov.uncovered_regions:
            entry["uncovered_regions"] = sorted(cov.uncovered_regions)

        files[source_path] = entry

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


def _is_int_list(value, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and \
        all(_is_non_negative_int(v) for v in value)


def _get_line_branches(source_path: str, entry: dict) -> list[list[int]]:
    """ Validate the [line, hit, found] items of 'line_branches'. """
    items = entry.get("line_branches", [])
    error = CoverageFileError(
        f"'line_branches' of '{source_path}' must be a list of "
        "[line, hit, found] items with distinct positive line numbers and "
        f"hit <= found <= {MAX_VALUE}.")

    if not isinstance(items, list):
        raise error

    lines = set()
    for item in items:
        if not _is_int_list(item, 3) or item[0] == 0 or \
                item[1] > item[2] or item[0] in lines:
            raise error
        lines.add(item[0])

    return sorted(list(item) for item in items)


def _get_line_mcdc(source_path: str, entry: dict) -> list[list]:
    """ Validate the [line, hit, found, [labels]] items of 'line_mcdc'. """
    items = entry.get("line_mcdc", [])
    error = CoverageFileError(
        f"'line_mcdc' of '{source_path}' must be a list of "
        "[line, hit, found, [labels]] items with distinct positive line "
        f"numbers, hit <= found <= {MAX_VALUE} and at most {MAX_LABELS} "
        f"labels of at most {MAX_LABEL_LENGTH} characters.")

    if not isinstance(items, list):
        raise error

    lines = set()
    for item in items:
        if not isinstance(item, list) or len(item) != 4 or \
                not _is_int_list(item[:3], 3) or item[0] == 0 or \
                item[1] > item[2] or item[0] in lines:
            raise error

        labels = item[3]
        if not isinstance(labels, list) or len(labels) > MAX_LABELS or \
                not all(isinstance(label, str) and
                        len(label) <= MAX_LABEL_LENGTH for label in labels):
            raise error

        lines.add(item[0])

    return sorted([item[0], item[1], item[2], list(item[3])]
                  for item in items)


def _get_uncovered_regions(
    source_path: str,
    entry: dict
) -> list[list[int]]:
    """ Validate the [line1, col1, line2, col2] items of the regions. """
    items = entry.get("uncovered_regions", [])
    error = CoverageFileError(
        f"'uncovered_regions' of '{source_path}' must be a list of "
        "[start line, start column, end line, end column] items of positive "
        f"numbers not greater than {MAX_VALUE} where the start is not after "
        "the end.")

    if not isinstance(items, list):
        raise error

    for item in items:
        if not _is_int_list(item, 4) or 0 in item or \
                (item[0], item[1]) > (item[2], item[3]):
            raise error

    return [list(r) for r in sorted({tuple(item) for item in items})]


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

        counts = {}
        for found_key, hit_key in COUNT_KEYS:
            counts[found_key] = _get_count(source_path, entry, found_key)
            counts[hit_key] = _get_count(source_path, entry, hit_key)
            if counts[hit_key] > counts[found_key]:
                raise CoverageFileError(
                    f"'{hit_key}' of '{source_path}' is greater than "
                    f"'{found_key}'.")

        result[source_path] = FileCoverage(
            sorted(covered), sorted(uncovered),
            functions_found, functions_hit,
            line_branches=_get_line_branches(source_path, entry),
            line_mcdc=_get_line_mcdc(source_path, entry),
            uncovered_regions=_get_uncovered_regions(source_path, entry),
            **counts)

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
