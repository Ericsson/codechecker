# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Command line module.
"""


import json


class CmdLineOutputEncoder(json.JSONEncoder):
    # pylint: disable=method-hidden
    def default(self, o):
        d = {}
        d.update(o.__dict__)
        return d
