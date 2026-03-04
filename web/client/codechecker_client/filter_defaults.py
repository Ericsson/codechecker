# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Shared default values for CLI filter arguments.

Extracted into its own module so that both ``cli/cmd.py`` and
``cmd_line_client.py`` can import it without creating a circular dependency.
"""

DEFAULT_FILTER_VALUES = {
    'review_status': ['unreviewed', 'confirmed'],
    'detection_status': ['new', 'reopened', 'unresolved'],
    'uniqueing': 'off',
    'anywhere_on_report_path': False,
    'single_origin_report': False,
}
