# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Clang Static analyzer configuration handler.
"""
import os

from codechecker_analyzer import env
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
        self.ctu_dir = ''
        self.ctu_on_demand = False
        self.log_file = ''
        self.path_env_extra = ''
        self.ld_lib_path_extra = ''
        self.enable_z3 = False
        self.enable_z3_refutation = False
        self.environ = environ
        self.version_info = None

    @property
    def analyzer_plugins(self):
        """ Full path of the analyzer plugins. """
        plugin_dir = self.analyzer_plugins_dir

        clangsa_plugin_dir = env.get_clangsa_plugin_dir()
        is_analyzer_from_path = env.is_analyzer_from_path()
        if is_analyzer_from_path:
            if not clangsa_plugin_dir:
                return []

            # If the CC_ANALYZERS_FROM_PATH and CC_CLANGSA_PLUGIN_DIR
            # environment variables are set we will use this value as the
            # plugin directory.
            plugin_dir = clangsa_plugin_dir

        if not plugin_dir or not os.path.exists(plugin_dir):
            return []

        return [os.path.join(plugin_dir, f)
                for f in os.listdir(plugin_dir)
                if os.path.isfile(os.path.join(plugin_dir, f))
                and f.endswith(".so")]

    @property
    def ctu_capability(self):
        return CTUAutodetection(self.analyzer_binary, self.environ)
