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

    def get_reports(self, file_path: str) -> List[Report]:
        """Get reports from the given PMD JSON file."""
        return PMDParser().get_reports(file_path)

    def _add_report_hash(self, report: Report):
        report.report_hash = get_report_hash(
            report,
            HashType.PATH_SENSITIVE,
        )
