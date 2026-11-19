# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from collections import defaultdict
import json
import logging
import os
from typing import Iterable

from codechecker_report_converter.analyzers.analyzer_result import \
    AnalyzerResultBase
from codechecker_report_converter.report import coverage
from codechecker_report_converter.report import Report


LOG = logging.getLogger('report-converter')

# Value of the 'type' key of the files written by 'llvm-cov export'.
EXPORT_TYPE = 'llvm.coverage.json.export'

# Kind of the code regions in the 'regions' of the exported functions
# (llvm::coverage::CounterMappingRegion::CodeRegion).
CODE_REGION_KIND = 0

# Keys of the summary of an exported file -> coverage file keys.
SUMMARY_KEYS = {
    'functions': ('functions_found', 'functions_hit'),
    'regions': ('regions_found', 'regions_hit'),
    'branches': ('branches_found', 'branches_hit'),
    'mcdc': ('mcdc_found', 'mcdc_hit'),
}

Range = tuple[int, int, int, int]


def _list(value) -> list:
    """ Returns the given value if it is a list, otherwise an empty list. """
    return value if isinstance(value, list) else []


def _is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) \
        and value >= 0


def _get_range(item) -> Range | None:
    """
    Returns the (start line, start column, end line, end column) of the
    given region-like list, or None if it is malformed or the range can not
    be stored.
    """
    if not isinstance(item, list) or len(item) < 4 or \
            not all(_is_count(v) and 0 < v <= coverage.MAX_VALUE
                    for v in item[:4]):
        return None

    rng = (item[0], item[1], item[2], item[3])
    return rng if rng[:2] <= rng[2:] else None


def get_line_counts(segments: list) -> dict[int, int]:
    """
    Compute the execution count of the lines from the coverage segments of a
    file. The lines which are not in the result are not executable.

    This is a port of 'llvm::coverage::LineCoverageStats' which is used by
    'llvm-cov show' and 'llvm-cov report', so the result is the same as the
    line coverage reported by LLVM. A segment is a [line, column, count,
    has count, is region entry, is gap region] list.
    """
    segs = [s for s in _list(segments)
            if isinstance(s, list) and len(s) >= 6 and _is_count(s[0]) and
            0 < s[0] <= coverage.MAX_VALUE and _is_count(s[2])]
    segs.sort(key=lambda s: s[0])
    if not segs:
        return {}

    def is_start_of_region(seg) -> bool:
        return bool(seg[3]) and bool(seg[4]) and not seg[5]

    result: dict[int, int] = {}

    # The last segment of the previous lines, empty if there is none.
    wrapped: list = []
    idx = 0
    line = segs[0][0]
    last_line = segs[-1][0]

    while line <= last_line:
        line_segs = []
        while idx < len(segs) and segs[idx][0] == line:
            line_segs.append(segs[idx])
            idx += 1

        starts = [s for s in line_segs if is_start_of_region(s)]
        start_of_skipped = bool(line_segs) and not line_segs[0][3] and \
            bool(line_segs[0][4])

        wrapped_has_count = bool(wrapped) and bool(wrapped[3])
        if not start_of_skipped and (wrapped_has_count or starts):
            count = wrapped[2] if wrapped else 0
            result[line] = max([count] + [s[2] for s in starts])

        if line_segs:
            wrapped = line_segs[-1]

        line += 1

        # The lines without segments after a region without count are not
        # executable, so they are skipped.
        if idx < len(segs) and segs[idx][0] > line and \
                not (wrapped and wrapped[3]):
            line = segs[idx][0]

    return result


class _SourceCoverage:
    """ Coverage of a source file collected from 'llvm-cov export' data. """

    def __init__(self) -> None:
        # Line number -> execution count.
        self.line_counts: dict[int, int] = {}

        # Coverage file key -> value. Taken from the summary of the file.
        self.counts: dict[str, int] = defaultdict(int)

        # Branch range -> [true count, false count].
        self.branches: dict[Range, list[int]] = {}

        # Decision range -> covered flag of each condition.
        self.mcdc: dict[Range, list[bool]] = {}

        # Code region range -> execution count.
        self.regions: dict[Range, int] = {}

        # Number of exported file entries of this source file.
        self.exports = 0

    def add_lines(self, segments: list):
        for line, count in get_line_counts(segments).items():
            self.line_counts[line] = max(self.line_counts.get(line, 0), count)

    def add_summary(self, summary: dict):
        """
        The counts of the same file in multiple exports are not summed up,
        because they are usually coverage of the same code by different test
        runs: the maximum is kept.
        """
        for summary_key, (found_key, hit_key) in SUMMARY_KEYS.items():
            item = summary.get(summary_key)
            if not isinstance(item, dict):
                continue

            found, hit = item.get('count'), item.get('covered')
            if not _is_count(found) or not _is_count(hit):
                continue

            found = min(found, coverage.MAX_VALUE)
            self.counts[found_key] = max(self.counts[found_key], found)
            self.counts[hit_key] = max(self.counts[hit_key], min(hit, found))

    def add_branches(self, branches: list):
        """
        A branch is a [line1, col1, line2, col2, true count, false count,
        file id, expanded file id, kind] list.
        """
        for branch in _list(branches):
            rng = _get_range(branch)
            if rng is None or len(branch) < 6 or \
                    not _is_count(branch[4]) or not _is_count(branch[5]):
                continue

            counts = self.branches.setdefault(rng, [0, 0])
            counts[0] = min(counts[0] + branch[4], coverage.MAX_VALUE)
            counts[1] = min(counts[1] + branch[5], coverage.MAX_VALUE)

    def add_mcdc_records(self, records: list):
        """
        An MC/DC record is a [line1, col1, line2, col2, ..., [covered flag
        of each condition]] list. Only the range and the last element are
        read, because the elements between them differ by LLVM versions.
        """
        for record in _list(records):
            rng = _get_range(record)
            if rng is None or not isinstance(record[-1], list) or \
                    not all(isinstance(c, bool) for c in record[-1]):
                continue

            conditions = record[-1]
            prev = self.mcdc.get(rng, [])
            self.mcdc[rng] = [
                (i < len(prev) and prev[i]) or
                (i < len(conditions) and conditions[i])
                for i in range(max(len(prev), len(conditions)))]

    def add_region(self, region: list):
        """
        A region is a [line1, col1, line2, col2, count, file id, expanded
        file id, kind] list. A region of a template which has multiple
        instances is uncovered only if none of its instances were executed.
        """
        rng = _get_range(region)
        if rng is None or not _is_count(region[4]):
            return

        self.regions[rng] = max(self.regions.get(rng, 0), region[4])

    def to_file_coverage(self) -> coverage.FileCoverage:
        covered = [ln for ln, cnt in self.line_counts.items() if cnt > 0]
        uncovered = [ln for ln, cnt in self.line_counts.items() if cnt == 0]

        line_branches: dict[int, list[int]] = {}
        for rng, counts in self.branches.items():
            item = line_branches.setdefault(rng[0], [0, 0])
            item[0] += sum(1 for c in counts if c > 0)
            item[1] += 2

        # The summary of a single export equals 'llvm-cov report'. The
        # summaries of multiple exports can not be merged, so the counts
        # are derived from the merged details instead.
        counts = dict(self.counts)
        if self.exports > 1:
            derived = {
                'regions': (len(self.regions),
                            sum(1 for c in self.regions.values() if c > 0)),
                'branches': (2 * len(self.branches),
                             sum(1 for cnts in self.branches.values()
                                 for c in cnts if c > 0)),
                'mcdc': (sum(len(c) for c in self.mcdc.values()),
                         sum(1 for conds in self.mcdc.values()
                             for c in conds if c)),
            }
            for key, (found, hit) in derived.items():
                found_key, hit_key = SUMMARY_KEYS[key]
                if found:
                    counts[found_key] = min(found, coverage.MAX_VALUE)
                    counts[hit_key] = min(hit, coverage.MAX_VALUE)

        line_mcdc: dict[int, list] = {}
        for rng, conditions in sorted(self.mcdc.items()):
            item = line_mcdc.setdefault(rng[0], [0, 0, []])
            item[0] += sum(1 for c in conditions if c)
            item[1] += len(conditions)
            for i, is_covered in enumerate(conditions):
                if not is_covered and len(item[2]) < coverage.MAX_LABELS:
                    item[2].append(f"C{i + 1}")

        return coverage.FileCoverage(
            sorted(covered), sorted(uncovered),
            line_branches=[[line, min(hit, coverage.MAX_VALUE),
                            min(found, coverage.MAX_VALUE)]
                           for line, (hit, found)
                           in sorted(line_branches.items())],
            line_mcdc=[[line, min(hit, coverage.MAX_VALUE),
                        min(found, coverage.MAX_VALUE), labels]
                       for line, (hit, found, labels)
                       in sorted(line_mcdc.items())],
            uncovered_regions=sorted(
                list(rng) for rng, count in self.regions.items()
                if count == 0),
            **counts)


class AnalyzerResult(AnalyzerResultBase):
    """ Transform 'llvm-cov export' JSON files to a CodeChecker coverage
    file. """

    TOOL_NAME = 'llvm-cov'
    NAME = 'LLVM source-based test coverage'
    URL = 'https://llvm.org/docs/CommandGuide/llvm-cov.html'

    EXAMPLE_CMD = """\
# Build the project with source-based coverage instrumentation and run its
# tests. For MC/DC coverage (Clang 18+) add '-fcoverage-mcdc' to CFLAGS.
make CC=clang CFLAGS="-fprofile-instr-generate -fcoverage-mapping" \\
  LDFLAGS="-fprofile-instr-generate"
LLVM_PROFILE_FILE="test-%p.profraw" make test

# Merge every raw profile into one and export the coverage data once.
llvm-profdata merge -sparse test-*.profraw -o test.profdata
llvm-cov export -format=text -instr-profile=test.profdata ./my_binary \\
  > coverage.json

# Use 'report-converter' to create a CodeChecker report directory from the
# exported data. The coverage data is written to 'coverage/coverage.json'.
report-converter -t llvm-cov -o ./codechecker_llvm_cov_reports \\
  ./coverage.json

# Store the coverage data to the CodeChecker server. Store it together with
# the analysis results of the same run, because each store replaces the
# reports of the run.
CodeChecker store ./reports ./codechecker_llvm_cov_reports -n my_run"""

    def transform(
        self,
        analyzer_result_file_paths: Iterable[str],
        output_dir_path: str,
        export_type: str,
        file_name: str = "{source_file}_{analyzer}_{file_hash}",
        metadata: dict[str, str] | None = None
    ) -> bool:
        """
        Merge the given 'llvm-cov export' files and write the coverage of the
        source files to the coverage file of the output directory. No
        analyzer report files are created.
        """
        sources: dict[str, _SourceCoverage] = defaultdict(_SourceCoverage)

        for file_path in analyzer_result_file_paths:
            self._parse_export_file(os.path.abspath(file_path), sources)

        if not sources:
            LOG.error("No '%s' coverage data can be found in the given "
                      "input files.", self.TOOL_NAME)
            return False

        out_path = coverage.get_coverage_file_path(output_dir_path)
        coverage.write(
            out_path,
            {path: src.to_file_coverage() for path, src in sources.items()},
            self.TOOL_NAME)

        if metadata:
            self._save_metadata(metadata, output_dir_path)

        LOG.info("Coverage data of %d source file(s) was written to '%s'.",
                 len(sources), out_path)
        return True

    def get_reports(self, file_path: str) -> list[Report]:
        """ 'llvm-cov export' files contain no analyzer reports. """
        return []

    @staticmethod
    def _parse_export_file(
        file_path: str,
        sources: dict[str, _SourceCoverage]
    ):
        """
        Parse the given 'llvm-cov export -format=text' file and merge its
        data into 'sources'.
        """
        try:
            with open(file_path, 'r', encoding='utf-8',
                      errors='replace') as f:
                data = json.load(f)
        except (OSError, ValueError) as err:
            LOG.error("Failed to read 'llvm-cov export' file '%s': %s",
                      file_path, err)
            return

        if not isinstance(data, dict) or data.get('type') != EXPORT_TYPE or \
                not isinstance(data.get('data'), list):
            LOG.error("'%s' is not an 'llvm-cov export -format=text' file.",
                      file_path)
            return

        for export in data['data']:
            if not isinstance(export, dict):
                continue

            for file_entry in _list(export.get('files')):
                if not isinstance(file_entry, dict) or \
                        not isinstance(file_entry.get('filename'), str) or \
                        not file_entry['filename']:
                    continue

                # Relative source paths are resolved against the current
                # working directory, like 'llvm-cov show' does.
                src = sources[os.path.abspath(file_entry['filename'])]
                src.exports += 1
                src.add_lines(file_entry.get('segments'))
                src.add_branches(file_entry.get('branches'))
                src.add_mcdc_records(file_entry.get('mcdc_records'))
                if isinstance(file_entry.get('summary'), dict):
                    src.add_summary(file_entry['summary'])

            # The code regions are listed only by the functions.
            for function in _list(export.get('functions')):
                if not isinstance(function, dict):
                    continue

                filenames = _list(function.get('filenames'))
                for region in _list(function.get('regions')):
                    if not isinstance(region, list) or len(region) < 8 or \
                            region[7] != CODE_REGION_KIND or \
                            not _is_count(region[5]) or \
                            region[5] >= len(filenames) or \
                            not isinstance(filenames[region[5]], str):
                        continue

                    path = os.path.abspath(filenames[region[5]])
                    if path in sources:
                        sources[path].add_region(region)
