# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import json
import os
from typing import List

from codechecker_report_converter.report import (
    BugPathEvent,
    Report,
    get_or_create_file,
)


class PMDParser:
    """Parser for PMD JSON output."""

    def __init__(self):
        self._file_cache = {}

    def get_reports(self, file_path: str) -> List[Report]:
        reports: List[Report] = []

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        for file_entry in data.get("files", []):
            filename = os.path.abspath(file_entry["filename"])

            for violation in file_entry.get("violations", []):
                line = violation.get("beginline", 1)
                column = violation.get("begincolumn", 1)
                message = violation.get("description", "")
                checker_name = violation.get("rule", "unknown")

                report = Report(
                    get_or_create_file(filename, self._file_cache),
                    line,
                    column,
                    message,
                    checker_name,
                    bug_path_events=[],
                )

                report.bug_path_events.append(
                    BugPathEvent(
                        message,
                        report.file,
                        report.line,
                        report.column,
                    )
                )

                report.category = violation.get("ruleset", "unknown")
                reports.append(report)

        return reports
