# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Command line module.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json


class CmdLineOutputEncoder(json.JSONEncoder):
    # pylint: disable=method-hidden
    def default(self, o):
        d = {}
        d.update(o.__dict__)
        return d
