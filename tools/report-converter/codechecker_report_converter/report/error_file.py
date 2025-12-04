# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os

from codechecker_report_converter.report.parser import plist


def update(output_path, return_code, analyzer_info,
           analyzer_cmd, stdout, stderr):

    plist_err_path = output_path + ".err"

    # Remove existing plist.err file
    try:
        os.remove(plist_err_path)
    except OSError:
        pass

    if return_code == 0:
        return

    parser = plist.Parser()

    data = {
        'analyzer_name': analyzer_info.name,
        'analyzer_cmd': analyzer_cmd,
        'return_code': return_code,
        'stdout': stdout,
        'stderr': stderr
    }

    parser.write(data, plist_err_path)
