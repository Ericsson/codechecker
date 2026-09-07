# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import os
import sys

from collections import defaultdict, namedtuple
from typing import Dict, Optional, Tuple

from codechecker_report_converter import twodim
from codechecker_report_converter.report import Report


LOG = logging.getLogger('report-converter')


Checker = namedtuple('Checker', ['name', 'severity'])


class Statistics:
    def __init__(self):
        self.num_of_analyzer_result_files = 0
        self.num_of_reports = 0

        self.severity_statistics = defaultdict(int)
        self.checker_statistics = defaultdict(int)
        self.file_statistics = defaultdict(int)

        # analyzer name -> {source file: (duration in seconds,
        #                                  peak memory usage in bytes)}.
        self.duration_statistics: \
            Dict[str, Dict[str, Tuple[float, float]]] = defaultdict(dict)

    def _write_severity_statistics(self, out=sys.stdout):
        """ Print severity statistics if it's available. """
        if not self.severity_statistics:
            return

        out.write("\n----==== Severity Statistics ====----\n")
        header = ["Severity", "Number of reports"]
        out.write(twodim.to_table(
            [header] + list(self.severity_statistics.items())))
        out.write("\n----=================----\n")

    def _write_checker_statistics(self, out=sys.stdout):
        """ Print checker statistics if it's available. """
        if not self.checker_statistics:
            return

        out.write("\n----==== Checker Statistics ====----\n")
        header = ["Checker name", "Severity", "Number of reports"]
        out.write(twodim.to_table([header] + [
            (c.name, c.severity, n)
            for (c, n) in self.checker_statistics.items()]))
        out.write("\n----=================----\n")

    def _write_file_statistics(self, out=sys.stdout):
        """ Print file statistics if it's available. """
        if not self.file_statistics:
            return

        out.write("\n----==== File Statistics ====----\n")
        header = ["File name", "Number of reports"]
        out.write(twodim.to_table([header] + [
            (os.path.basename(file_path), n)
            for (file_path, n) in self.file_statistics.items()]))
        out.write("\n----=================----\n")

    def _write_per_file_table(
        self, out, title: str, subtitle: str,
        get_value, format_value
    ):
        """ Print a per-file, per-analyzer top-10 table built from
        'duration_statistics', if available. """
        if not self.duration_statistics:
            return

        analyzer_names = list(self.duration_statistics.keys())

        def _value(a: str, f: str) -> float:
            return get_value(self.duration_statistics[a].get(f, (0.0, 0.0)))

        all_files = sorted(
            {f for d in self.duration_statistics.values() for f in d},
            key=lambda f: sum(_value(a, f) for a in analyzer_names),
            reverse=True
        )[:10]

        if not all_files:
            return

        header = ["File"] + analyzer_names + ["Total"]
        rows = []
        for src in all_files:
            total = sum(_value(a, src) for a in analyzer_names)
            rows.append(
                [src] +
                [format_value(_value(a, src)) for a in analyzer_names] +
                [format_value(total)])

        analyzer_sums = [
            sum(get_value(v) for v in self.duration_statistics[a].values())
            for a in analyzer_names]
        rows.append(
            ["Sum"] +
            [format_value(s) for s in analyzer_sums] +
            [format_value(sum(analyzer_sums))])

        out.write(f"\n----==== {title} ====----\n")
        out.write(subtitle + "\n")
        out.write(twodim.to_table(
            [header] + rows,
            ellipsis_columns=range(len(header)),
            keep_suffix_columns=[0]))
        out.write("\n----=================----\n")

    def _write_duration_statistics(self, out=sys.stdout):
        """ Print the top 10 slowest files to analyze, if available. """
        self._write_per_file_table(
            out, "Per-File Analysis Duration Statistics",
            "Top 10 slowest files (seconds):",
            get_value=lambda t: t[0],
            format_value=lambda v: f"{v:.2f}s")

    def _write_memory_statistics(self, out=sys.stdout):
        """ Print the top 10 most memory-hungry files to analyze,
        if available. """
        self._write_per_file_table(
            out, "Per-File Analysis Memory Statistics",
            "Top 10 most memory-hungry files (MB):",
            get_value=lambda t: t[1] / 2**20,
            format_value=lambda v: f"{v:.1f}MB")

    def _write_summary(self, out=sys.stdout):
        """ Print summary. """
        out.write("\n----======== Summary ========----\n")
        statistics_rows = [
            ["Number of processed analyzer result files",
             str(self.num_of_analyzer_result_files)],
            ["Number of analyzer reports", str(self.num_of_reports)]]
        out.write(twodim.to_table(
            statistics_rows, False, separate_footer=True))
        out.write("\n----=================----\n")

    def write(self, _=sys.stdout):
        """ Print statistics. """
        self._write_severity_statistics()
        self._write_checker_statistics()
        self._write_file_statistics()
        self._write_duration_statistics()
        self._write_memory_statistics()
        self._write_summary()

    def add_report(self, report: Report):
        """ Collect statistics from the given report. """
        self.num_of_reports += 1
        self.severity_statistics[report.severity] += 1
        self.checker_statistics[
            Checker(report.checker_name, report.severity)] += 1
        self.file_statistics[report.file.original_path] += 1

    def add_analyzer_durations(self, metadata: Optional[Dict]):
        """ Collect per-file analyzer durations and peak memory usage from
        an analysis 'metadata.json' contents. """
        if not metadata:
            return

        for tool in metadata.get('tools', []):
            for analyzer_name, analyzer_data in \
                    tool.get('analyzers', {}).items():
                durations = analyzer_data.get(
                    'analyzer_statistics', {}).get('duration_of_sources', [])
                for src, duration, peak_memory in durations:
                    self.duration_statistics[analyzer_name][src] = \
                        (duration, peak_memory)
