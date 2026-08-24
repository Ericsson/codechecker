# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from typing import List

from codechecker_report_converter.report import Report
from codechecker_report_converter.report.hash import (
    HashType,
    get_report_hash,
)

from ..analyzer_result import AnalyzerResultBase
from .parser import PMDParser


class AnalyzerResult(AnalyzerResultBase):
    """Transform analyzer result of PMD JSON."""

    TOOL_NAME = "pmd"
    NAME = "PMD"
    URL = "https://pmd.github.io/"

    EXAMPLE_CMD = """\
# Run PMD and generate a json report.
pmd check -d /path/to/my/project -R rulesets/java/quickstart.xml \\
    -f json -r ./pmd_reports.json

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of PMD.
report-converter -t pmd -o ./codechecker_pmd_reports ./pmd_reports.json

# Store the PMD reports with CodeChecker.
CodeChecker store ./codechecker_pmd_reports -n pmd"""

    def get_reports(self, file_path: str) -> List[Report]:
        """Get reports from the given PMD JSON file."""
        return PMDParser().get_reports(file_path)

    def _add_report_hash(self, report: Report):
        report.report_hash = get_report_hash(
            report,
            HashType.PATH_SENSITIVE,
        )
