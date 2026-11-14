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

        # (line, block, branch) -> execution count of the branch.
        self.branch_hits: dict[tuple[int, str, str], int] = defaultdict(int)

        # (line, group size, condition index, sense) -> number of times the
        # condition was shown to independently affect the outcome of its
        # decision with the given sense, and the expression of the condition.
        self.mcdc_hits: dict[tuple[int, int, int, bool], int] = \
            defaultdict(int)
        self.mcdc_expressions: dict[tuple[int, int, int, bool], str] = {}

        # Values of the FNF and FNH summary records. These are used only if
        # the tracefile does not list the functions one by one. The same
        # holds for the BRF/BRH and MCF/MCH records.
        self.functions_found = 0
        self.functions_hit = 0
        self.branches_found = 0
        self.branches_hit = 0
        self.mcdc_found = 0
        self.mcdc_hit = 0

    @staticmethod
    def _per_line(hits: dict) -> dict[int, list[int]]:
        """ Line -> [hit, found] of the given records. """
        result: dict[int, list[int]] = {}
        for key, count in hits.items():
            item = result.setdefault(key[0], [0, 0])
            item[0] += 1 if count > 0 else 0
            item[1] += 1
        return result

    def _mcdc_label(self, key: tuple[int, int, int, bool]) -> str:
        """ Name of an MC/DC condition shown to the user. """
        expression = self.mcdc_expressions.get(key, '')
        name = expression if expression and not expression.isdigit() \
            else f"C{key[2] + 1}"
        sense = 'true' if key[3] else 'false'

        # The label must fit in the limit of the coverage file.
        max_name_length = coverage.MAX_LABEL_LENGTH - len(sense) - 1
        if len(name) > max_name_length:
            name = name[:max_name_length - 3] + '...'
        return f"{name} {sense}"

    def _branch_coverage(self) -> dict:
        """ Branch and MC/DC fields of the coverage of this file. """
        result = {}

        if self.branch_hits:
            per_line = self._per_line(self.branch_hits)
            result['line_branches'] = [
                [line, hit, found]
                for line, (hit, found) in sorted(per_line.items())]
            result['branches_found'] = min(
                len(self.branch_hits), coverage.MAX_VALUE)
            result['branches_hit'] = min(
                sum(hit for hit, _ in per_line.values()), coverage.MAX_VALUE)
        else:
            result['branches_found'] = self.branches_found
            result['branches_hit'] = min(
                self.branches_hit, self.branches_found)

        if self.mcdc_hits:
            per_line = self._per_line(self.mcdc_hits)
            uncovered: dict[int, list[str]] = defaultdict(list)
            for key, count in sorted(self.mcdc_hits.items()):
                if count == 0 and \
                        len(uncovered[key[0]]) < coverage.MAX_LABELS:
                    uncovered[key[0]].append(self._mcdc_label(key))

            result['line_mcdc'] = [
                [line, hit, found, uncovered.get(line, [])]
                for line, (hit, found) in sorted(per_line.items())]
            result['mcdc_found'] = min(
                len(self.mcdc_hits), coverage.MAX_VALUE)
            result['mcdc_hit'] = min(
                sum(hit for hit, _ in per_line.values()), coverage.MAX_VALUE)
        else:
            result['mcdc_found'] = self.mcdc_found
            result['mcdc_hit'] = min(self.mcdc_hit, self.mcdc_found)

        return result

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
            functions_found, functions_hit,
            **self._branch_coverage())


def _to_line(value: str) -> int | None:
    """ Convert the given LCOV field to a line number which can be stored. """
    line_no = _to_int(value)
    return line_no if line_no and line_no <= coverage.MAX_VALUE else None


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
        'FNL'/'FNA' records of LCOV 2.2+ are supported, as well as the 'BRDA'
        branch and the 'MCDC' condition records (LCOV 2.2+, GCC 14+ with
        '-fcondition-coverage'). Records with the same key are summed up.
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
            elif key == 'BRDA' and len(fields) >= 4:
                # BRDA:<line>,[e]<block>,<branch>,<taken>
                # The taken field is '-' if the block was never executed.
                line_no = _to_line(fields[0])
                taken = 0 if fields[-1] == '-' else _to_int(fields[-1])
                if line_no and taken is not None:
                    branch_key = (line_no, fields[1], ','.join(fields[2:-1]))
                    current.branch_hits[branch_key] = min(
                        current.branch_hits[branch_key] + taken,
                        coverage.MAX_VALUE)
            elif key == 'MCDC' and len(fields) >= 5:
                # MCDC:<line>,<group size>,<t|f>,<taken>,<index>,<expression>
                line_no = _to_line(fields[0])
                group_size = _to_int(fields[1])
                taken = _to_int(fields[3])
                index = _to_int(fields[4])
                if line_no and group_size is not None and \
                        fields[2] in ('t', 'f') and taken is not None and \
                        index is not None:
                    mcdc_key = (line_no, group_size, index, fields[2] == 't')
                    current.mcdc_hits[mcdc_key] = min(
                        current.mcdc_hits[mcdc_key] + taken,
                        coverage.MAX_VALUE)
                    current.mcdc_expressions.setdefault(
                        mcdc_key, ','.join(fields[5:]).strip())
            elif key in ('BRF', 'BRH', 'MCF', 'MCH'):
                attr = {'BRF': 'branches_found', 'BRH': 'branches_hit',
                        'MCF': 'mcdc_found', 'MCH': 'mcdc_hit'}[key]
                setattr(current, attr, max(
                    getattr(current, attr),
                    min(_to_int(value) or 0, coverage.MAX_VALUE)))
            elif key == 'FNF':
                current.functions_found = max(
                    current.functions_found,
                    min(_to_int(value) or 0, coverage.MAX_VALUE))
            elif key == 'FNH':
                current.functions_hit = max(
                    current.functions_hit,
                    min(_to_int(value) or 0, coverage.MAX_VALUE))
