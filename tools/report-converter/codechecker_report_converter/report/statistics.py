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

    def write(self, out=sys.stdout):
        """ Print statistics. """
        if self.severity_statistics:
            out.write("\n----==== Severity Statistics ====----\n")
            header = ["Severity", "Number of reports"]
            out.write(twodim.to_table(
                [header] + list(self.severity_statistics.items())))
            out.write("\n----=================----\n")

        if self.checker_statistics:
            out.write("\n----==== Checker Statistics ====----\n")
            header = ["Checker name", "Severity", "Number of reports"]
            out.write(twodim.to_table([header] + [
                (c.name, c.severity, n)
                for (c, n) in self.checker_statistics.items()]))
            out.write("\n----=================----\n")

        if self.file_statistics:
            out.write("\n----==== File Statistics ====----\n")
            header = ["File name", "Number of reports"]
            out.write(twodim.to_table([header] + [
                (os.path.basename(file_path), n)
                for (file_path, n) in self.file_statistics.items()]))
            out.write("\n----=================----\n")

        out.write("\n----======== Summary ========----\n")
        statistics_rows = [
            ["Number of processed analyzer result files",
             str(self.num_of_analyzer_result_files)],
            ["Number of analyzer reports", str(self.num_of_reports)]]
        out.write(twodim.to_table(statistics_rows, False))
        out.write("\n----=================----\n")

    def add_report(self, report: Report):
        """ Collect statistics from the given report. """
        self.num_of_reports += 1
        self.severity_statistics[report.severity] += 1
        self.checker_statistics[
            Checker(report.checker_name, report.severity)] += 1
        self.file_statistics[report.file.original_path] += 1
