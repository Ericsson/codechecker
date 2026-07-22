from typing import Dict, List, Optional

from codechecker_report_converter.report import Report
from codechecker_report_converter.report.checker_labels import CheckerLabels
from codechecker_report_converter.report.parser import sarif


def convert(
    reports: List[Report],
    checker_labels: Optional[CheckerLabels] = None
) -> Dict:
    sarif_parser = sarif.Parser(checker_labels=checker_labels)
    return sarif_parser.convert(reports)
