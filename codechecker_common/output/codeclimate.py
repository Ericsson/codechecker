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


def convert(reports: List[Report], repo_dirs: List[str]) -> Dict:
    """Convert the given reports to codeclimate format.

    This function will convert the given report to Code Climate format.
    reports - list of reports type Report
    repo_dir - Root directory of the sources, i.e. the directory where the
               repository was cloned, which will be trimmed if set.

    returns a list of reports converted to codeclimate format
    """
    codeclimate_reports = []
    for report in reports:
        if repo_dirs:
            report.trim_path_prefixes(repo_dirs)

        codeclimate_reports.append(__to_codeclimate(report))
    return codeclimate_reports


def __to_codeclimate(report: Report) -> Dict:
    """Convert a Report to Code Climate format."""
    location = report.main['location']
    _, file_name = os.path.split(location['file'])

    return {
        "type": "issue",
        "check_name": report.check_name,
        "description": report.description,
        "categories": ["Bug Risk"],
        "fingerprint": report.report_hash,
        "location": {
            "path": file_name,
            "lines": {
                "begin": location['line']
            }
        }
    }
