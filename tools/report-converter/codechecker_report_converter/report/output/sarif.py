from typing import Dict, List

from codechecker_report_converter.report import Report
from codechecker_report_converter.report.parser import sarif


def convert(reports: List[Report]) -> Dict:
    sarif_parser = sarif.Parser()
    return sarif_parser.convert(reports)
