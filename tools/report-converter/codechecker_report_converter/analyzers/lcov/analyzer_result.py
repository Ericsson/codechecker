# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import json
import logging
import os
import re
from typing import Dict, Iterable, List

from codechecker_report_converter.analyzers.analyzer_result import \
    AnalyzerResultBase


LOG = logging.getLogger('report-converter')


class AnalyzerResult(AnalyzerResultBase):
    """LCOV info file to coverage JSON mapping."""

    TOOL_NAME = 'lcov'
    NAME = 'LCOV coverage info to JSON'
    URL = 'https://github.com/linux-test-project/lcov'

    def transform(
        self,
        analyzer_result_file_paths: Iterable[str],
        output_dir_path: str,
        export_type: str,
        file_name: str = "{source_file}_{analyzer}_{file_hash}",
        metadata=None
    ) -> bool:
        coverage_map: Dict[str, Dict[int, int]] = {}
        function_map: Dict[str, Dict[str, int]] = {}

        for input_path in analyzer_result_file_paths:
            abs_input = os.path.abspath(input_path)
            parsed, funcs = self._parse_lcov_info(abs_input)
            for src, line_counts in parsed.items():
                if src not in coverage_map:
                    coverage_map[src] = {}
                for ln, cnt in line_counts.items():
                    coverage_map[src][ln] = \
                        coverage_map[src].get(ln, 0) + cnt
            for src, fdata in funcs.items():
                if src not in function_map:
                    function_map[src] = {"found": 0, "hit": 0}
                function_map[src]["found"] = max(
                    function_map[src]["found"], fdata["found"])
                function_map[src]["hit"] = max(
                    function_map[src]["hit"], fdata["hit"])

        if not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path)

        # Build output with function stats embedded
        output = {}
        for src, line_counts in coverage_map.items():
            covered = sorted(ln for ln, cnt in line_counts.items()
                             if cnt > 0)
            uncovered = sorted(ln for ln, cnt in line_counts.items()
                               if cnt == 0)
            entry = {"lines": covered, "uncovered": uncovered}
            if src in function_map:
                entry["functions_found"] = function_map[src]["found"]
                entry["functions_hit"] = function_map[src]["hit"]
            output[src] = entry

        out_path = os.path.join(output_dir_path, 'coverage', 'coverage.json')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, sort_keys=True)

        LOG.info("Created LCOV coverage JSON: '%s'", out_path)
        return bool(coverage_map)

    def get_reports(self, file_path: str):
        return []

    @staticmethod
    def _parse_lcov_info(info_path: str):
        """Parse an LCOV .info file.

        Returns (coverage_data, function_data) where:
        - coverage_data: {source -> {line_num: exec_count}} (all DA lines)
        - function_data: {source -> {found: N, hit: N}}
        """
        coverage_data: Dict[str, Dict[int, int]] = {}
        function_data: Dict[str, Dict[str, int]] = {}
        current_file = None
        line_data: Dict[int, int] = {}
        fnf = 0
        fnh = 0

        try:
            with open(info_path, 'r', encoding='utf-8',
                       errors='replace') as f:
                for raw in f:
                    line = raw.strip()

                    if line.startswith('SF:'):
                        if current_file:
                            abs_path = os.path.abspath(current_file)
                            if line_data:
                                existing = coverage_data.get(abs_path, {})
                                for ln, cnt in line_data.items():
                                    existing[ln] = existing.get(
                                        ln, 0) + cnt
                                coverage_data[abs_path] = existing
                            if fnf > 0:
                                function_data[abs_path] = {
                                    "found": fnf, "hit": fnh}
                        current_file = line[3:]
                        line_data = {}
                        fnf = 0
                        fnh = 0

                    elif line.startswith('DA:') and current_file:
                        match = re.match(r'DA:(\d+),(\d+)', line)
                        if match:
                            line_num = int(match.group(1))
                            exec_count = int(match.group(2))
                            line_data[line_num] = exec_count

                    elif line.startswith('FNF:') and current_file:
                        try:
                            fnf = int(line[4:])
                        except ValueError:
                            pass

                    elif line.startswith('FNH:') and current_file:
                        try:
                            fnh = int(line[4:])
                        except ValueError:
                            pass

                    elif line == 'end_of_record':
                        if current_file:
                            abs_path = os.path.abspath(current_file)
                            if line_data:
                                existing = coverage_data.get(abs_path, {})
                                for ln, cnt in line_data.items():
                                    existing[ln] = existing.get(
                                        ln, 0) + cnt
                                coverage_data[abs_path] = existing
                            if fnf > 0:
                                function_data[abs_path] = {
                                    "found": fnf, "hit": fnh}
                        current_file = None
                        line_data = {}
                        fnf = 0
                        fnh = 0

                if current_file:
                    abs_path = os.path.abspath(current_file)
                    if line_data:
                        existing = coverage_data.get(abs_path, {})
                        for ln, cnt in line_data.items():
                            existing[ln] = existing.get(ln, 0) + cnt
                        coverage_data[abs_path] = existing
                    if fnf > 0:
                        function_data[abs_path] = {
                            "found": fnf, "hit": fnh}

        except OSError as err:
            LOG.error("Failed to read LCOV info file '%s': %s",
                      info_path, err)
            return {}, {}

        return coverage_data, function_data
