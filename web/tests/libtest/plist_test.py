#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""Plist report file modifications functions for the tests."""


import os
import plistlib


def prefix_file_path(plist_file, path_prefix):
    """Every path in the plist file is prefixed with the path_prefix.

    The file path is extended only in case if it is relative.

    Keeping the source file list order is important because the
    report sections refer to the source files by index in the plist.
    """
    print("rewriting %s", plist_file)
    with open(plist_file, 'rb') as report_file:
        report_data = plistlib.loads(report_file.read())

        for i, _ in enumerate(report_data["files"]):
            report_data["files"][i] = os.path.join(path_prefix,
                                                   report_data["files"][i])
    with open(plist_file, 'wb') as report_file:
        plistlib.dump(report_data, report_file)
