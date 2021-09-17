# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" JSON output helpers. """

from typing import Dict, List

from codechecker_report_converter.report import Report


def convert(reports: List[Report]) -> Dict:
    """ Convert the given reports to JSON format. """
    version = 1

    json_reports = []
    for report in reports:
        json_reports.append(report.to_json())

    return {"version": version, "reports": json_reports}
