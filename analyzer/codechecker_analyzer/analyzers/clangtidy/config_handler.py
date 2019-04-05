# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Config handler for Clang Tidy analyzer.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import json
import re
import shlex

from codechecker_common.logger import get_logger

from .. import config_handler

LOG = get_logger('analyzer.tidy')


class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer.
    """

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
        if checker_name.startswith("Wno-") or checker_name.startswith("W"):
            self.add_checker(checker_name, enabled, None)
            return

        super(ClangTidyConfigHandler, self).set_checker_enabled(checker_name,
                                                                enabled)
