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

import shlex
import subprocess

from codechecker_common.logger import get_logger

from .. import config_handler

LOG = get_logger('analyzer.tidy')


def parse_checkers(tidy_output):
    """
    Parse clang tidy checkers list.
    Skip clang static analyzer checkers.
    Store them to checkers.
    """
    checkers = []

    for line in tidy_output.splitlines():
        line = line.strip()
        if not line or line.startswith('Enabled checks:') or \
           line.startswith('clang-analyzer-'):
            continue
        checkers.append((line, ''))

    return checkers


class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer.
    """

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()

    def get_analyzer_checkers(self, environ):
        """
        Return the list of the supported checkers.
        """
        analyzer_binary = self.analyzer_binary

        command = [analyzer_binary, "-list-checks", "-checks=*"]

        try:
            result = subprocess.check_output(command, env=environ,
                                             universal_newlines=True)
            return parse_checkers(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
        if checker_name.startswith("Wno-") or checker_name.startswith("W"):
            self.add_checker(checker_name, enabled, None)
            return

        super(ClangTidyConfigHandler, self).set_checker_enabled(checker_name,
                                                                enabled)
