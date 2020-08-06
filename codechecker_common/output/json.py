# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Helper and converter functions for json output format."""

from typing import Dict
from codechecker_common.report import Report


def convert_to_parse(report: Report) -> Dict:
    """Converts to a special json format for the parse command.

    This format is used by the parse command when the reports are printed
    to the stdout in json format.
    """
    ret = report.main
    ret["path"] = report.bug_path
    ret["files"] = [v for k, v in report.files.items()]

    return ret
