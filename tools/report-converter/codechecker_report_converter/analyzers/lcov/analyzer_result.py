# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from collections import defaultdict
import logging
import os
from typing import Iterable

from codechecker_report_converter.analyzers.analyzer_result import \
    AnalyzerResultBase
from codechecker_report_converter.report import coverage
from codechecker_report_converter.report import Report


LOG = logging.getLogger('report-converter')


class _SourceCoverage:
    """ Coverage of a source file collected from LCOV records. """

    def __init__(self) -> None:
        # Line number -> execution count.
        self.line_hits: dict[int, int] = defaultdict(int)

        # Function name -> execution count.
        self.function_hits: dict[str, int] = defaultdict(int)

        # Values of the FNF and FNH summary records. These are used only if
        # the tracefile does not list the functions one by one.
        self.functions_found = 0
        self.functions_hit = 0

    def to_file_coverage(self) -> coverage.FileCoverage:
        covered = [ln for ln, cnt in self.line_hits.items() if cnt > 0]
        uncovered = [ln for ln, cnt in self.line_hits.items() if cnt == 0]

        if self.function_hits:
            functions_found = len(self.function_hits)
            functions_hit = sum(
                1 for cnt in self.function_hits.values() if cnt > 0)
        else:
            functions_found = self.functions_found
            functions_hit = min(self.functions_hit, self.functions_found)

        return coverage.FileCoverage(
            sorted(covered), sorted(uncovered),
            functions_found, functions_hit)


def _to_int(value: str) -> int | None:
    """
    Convert the given LCOV field to a non-negative integer. Returns None if
    the field is not a number.
    """
    try:
        return max(int(value), 0)
    except ValueError:
        return None


class AnalyzerResult(AnalyzerResultBase):
    """ Transform LCOV tracefiles to a CodeChecker coverage file. """

    TOOL_NAME = 'lcov'
    NAME = 'LCOV test coverage'
    URL = 'https://github.com/linux-test-project/lcov'

    EXAMPLE_CMD = """\
# Build the project with coverage instrumentation and run its tests.
make CFLAGS="--coverage" LDFLAGS="--coverage"
make test

# Capture the coverage data into an LCOV tracefile.
lcov --capture --directory . --output-file coverage.info

# Use 'report-converter' to create a CodeChecker report directory from the
# LCOV tracefile. The coverage data is written to 'coverage/coverage.json'.
report-converter -t lcov -o ./codechecker_lcov_reports ./coverage.info

# Store the coverage data to the CodeChecker server. Store it together with
# the analysis results of the same run, because each store replaces the
# reports of the run.
CodeChecker store ./reports ./codechecker_lcov_reports -n my_run"""

    def transform(
        self,
        analyzer_result_file_paths: Iterable[str],
        output_dir_path: str,
        export_type: str,
        file_name: str = "{source_file}_{analyzer}_{file_hash}",
        metadata: dict[str, str] | None = None
    ) -> bool:
        """
        Merge the given LCOV tracefiles and write the coverage of the source
        files to the coverage file of the output directory. No analyzer
        report files are created.
        """
        sources: dict[str, _SourceCoverage] = defaultdict(_SourceCoverage)

        for file_path in analyzer_result_file_paths:
            self._parse_tracefile(os.path.abspath(file_path), sources)

        if not sources:
            LOG.info("No '%s' coverage data can be found in the given "
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
        """ LCOV tracefiles contain no analyzer reports. """
        return []

    @staticmethod
    def _parse_tracefile(
        file_path: str,
        sources: dict[str, _SourceCoverage]
    ):
        """
        Parse the given LCOV tracefile and merge its records into 'sources'.
        If a source file occurs multiple times (e.g. coverage of multiple test
        binaries), the execution counts are summed up.

        Both the 'FN'/'FNDA' function records of LCOV 1.x and the
        'FNL'/'FNA' records of LCOV 2.2+ are supported. Branch records are
        ignored.
        """
        try:
            with open(file_path, 'r', encoding='utf-8',
                      errors='replace') as f:
                lines = f.readlines()
        except OSError as err:
            LOG.error("Failed to read LCOV tracefile '%s': %s",
                      file_path, err)
            return

        current: _SourceCoverage | None = None

        for raw_line in lines:
            line = raw_line.strip()

            if line == 'end_of_record':
                current = None
                continue

            key, sep, value = line.partition(':')
            if not sep:
                continue

            if key == 'SF':
                # Relative source paths are resolved against the current
                # working directory, like 'genhtml' does.
                current = sources[os.path.abspath(value)]
                continue

            if current is None:
                continue

            fields = value.split(',')
            if key == 'DA' and len(fields) >= 2:
                # DA:<line>,<execution count>[,<checksum>]
                line_no, count = _to_int(fields[0]), _to_int(fields[1])
                # Line numbers which can not be stored are ignored.
                if line_no and line_no <= coverage.MAX_VALUE and \
                        count is not None:
                    current.line_hits[line_no] += count
            elif key == 'FN' and len(fields) >= 2:
                # FN:<line>[,<end line>],<function name>
                has_end_line = len(fields) >= 3 and fields[1].isdigit()
                name = ','.join(fields[2:] if has_end_line else fields[1:])
                current.function_hits[name] += 0
            elif key == 'FNDA' and len(fields) >= 2:
                # FNDA:<execution count>,<function name>
                count = _to_int(fields[0])
                if count is not None:
                    current.function_hits[','.join(fields[1:])] += count
            elif key == 'FNA' and len(fields) >= 3:
                # FNA:<index>,<execution count>,<function name>
                count = _to_int(fields[1])
                if count is not None:
                    current.function_hits[','.join(fields[2:])] += count
            elif key == 'FNF':
                current.functions_found = max(
                    current.functions_found,
                    min(_to_int(value) or 0, coverage.MAX_VALUE))
            elif key == 'FNH':
                current.functions_hit = max(
                    current.functions_hit,
                    min(_to_int(value) or 0, coverage.MAX_VALUE))
