# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Codeclimate output helpers."""

from typing import Dict, List

from codechecker_report_converter.report import Report


def convert(reports: List[Report]) -> List[Dict]:
    """Convert the given reports to codeclimate format.

    This function will convert the given report to Code Climate format.
    reports - list of reports type Report

    returns a list of reports converted to codeclimate format
    """
    codeclimate_reports = []

    for report in reports:
        codeclimate_reports.append(__to_codeclimate(report))

    return codeclimate_reports


__codeclimate_severity_map = {
    'CRITICAL': 'critical',
    'HIGH': 'major',
    'MEDIUM': 'minor',
    'LOW': 'minor',
    'STYLE': 'info',
    'UNSPECIFIED': 'info',
}


def __to_codeclimate(report: Report) -> Dict:
    """Convert a Report to Code Climate format."""
    severity = __codeclimate_severity_map.get(report.severity) \
        if report.severity else 'info'

    return {
        "type": "issue",
        "check_name": report.checker_name,
        "description": report.message,
        "categories": ["Bug Risk"],
        "fingerprint": report.report_hash,
        "severity": severity,
        "location": {
            "path": report.file.path,
            "lines": {
                "begin": report.line
            }
        }
    }
