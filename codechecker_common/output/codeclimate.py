# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Codeclimate output helpers."""

from typing import Dict, List

from codechecker_common.report import Report
from codechecker_common.checker_labels import CheckerLabels


def convert(reports: List[Report], checker_labels: CheckerLabels) -> Dict:
    """Convert the given reports to codeclimate format.

    This function will convert the given report to Code Climate format.
    reports - list of reports type Report

    returns a list of reports converted to codeclimate format
    """
    codeclimate_reports = []
    for report in reports:
        codeclimate_reports.append(__to_codeclimate(report, checker_labels))
    return codeclimate_reports


__codeclimate_severity_map = {
    'CRITICAL': 'critical',
    'HIGH': 'major',
    'MEDIUM': 'minor',
    'LOW': 'minor',
    'STYLE': 'info',
    'UNSPECIFIED': 'info',
}


def __to_codeclimate(report: Report, checker_labels: CheckerLabels) -> Dict:
    """Convert a Report to Code Climate format."""
    return {
        "type": "issue",
        "check_name": report.check_name,
        "description": report.description,
        "categories": ["Bug Risk"],
        "fingerprint": report.report_hash,
        "severity": __codeclimate_severity_map.get(
            checker_labels.label_of_checker(report.check_name, 'severity'),
            'info'),
        "location": {
            "path": report.file_path,
            "lines": {
                "begin": report.main['location']['line']
            }
        }
    }
