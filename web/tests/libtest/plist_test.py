#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""Plist report file modifications functions for the tests."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import io
import os
import plistlib


def prefix_file_path(plist_file, path_prefix):
    """Every path in the plist file is prefixed with the path_prefix.

    The file path is extended only in case if it is relative.

    Keeping the source file list order is important because the
    report sections refer to the source files by index in the plist.
    """
    print("rewriting %s", plist_file)
    with io.open(plist_file, 'r+') as report_file:
        report_data = plistlib.readPlistFromString(report_file.read())
        report_file.seek(0)

        for i, _ in enumerate(report_data["files"]):
            report_data["files"][i] = os.path.join(path_prefix,
                                                   report_data["files"][i])
        plist_str = plistlib.writePlistToString(report_data)
        report_file.truncate(0)  # clean the file content
        report_file.write(plist_str.decode("utf-8"))
