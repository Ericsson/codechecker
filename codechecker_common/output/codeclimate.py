# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Codeclimate output helpers."""

import os
from typing import Dict, List

from codechecker_common.report import Report


def convert(reports: List[Report]) -> Dict:
    """Convert the given reports to codeclimate format.

    This function will convert the given report to Code Climate format.
    reports - list of reports type Report

    returns a list of reports converted to codeclimate format
    """
    codeclimate_reports = []
    for report in reports:
        codeclimate_reports.append(__to_codeclimate(report))
    return codeclimate_reports


def __to_codeclimate(report: Report) -> Dict:
    """Convert a Report to Code Climate format."""
    _, file_name = os.path.split(report.file_path)

    return {
        "type": "issue",
        "check_name": report.check_name,
        "description": report.description,
        "categories": ["Bug Risk"],
        "fingerprint": report.report_hash,
        "location": {
            "path": file_name,
            "lines": {
                "begin": report.main['location']['line']
            }
        }
    }
