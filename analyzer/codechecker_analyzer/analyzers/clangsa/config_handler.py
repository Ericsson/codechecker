# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Clang Static analyzer configuration handler.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from codechecker_common.logger import get_logger
from .ctu_autodetection import CTUAutodetection

from .. import config_handler

LOG = get_logger('analyzer.clangsa')


class ClangSAConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for the clang static analyzer.
    """

    def __init__(self, environ):
        super(ClangSAConfigHandler, self).__init__()
        self.__checker_configs = []
        self.ctu_dir = ''
        self.log_file = ''
        self.path_env_extra = ''
        self.ld_lib_path_extra = ''
        self.enable_z3 = False
        self.enable_z3_refutation = False
        self.environ = environ

    def add_checker_config(self, config):
        """
        Add a (checker_name, key, value) tuple to the list.
        """
        self.__checker_configs.append(config)

    @property
    def ctu_capability(self):
        return CTUAutodetection(self.analyzer_binary, self.environ)
