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

import re

from libcodechecker.analyze.analyzers import config_handler
from libcodechecker.logger import get_logger

LOG = get_logger('analyzer.clangsa')


class ClangSAConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for the clang static analyzer.
    """

    def __init__(self):
        super(ClangSAConfigHandler, self).__init__()
        self.__checker_configs = []
        self.ctu_dir = ''
        self.log_file = ''
        self.path_env_extra = ''
        self.ld_lib_path_extra = ''

    def add_checker_config(self, config):
        """
        Add a (checker_name, key, value) tuple to the list.
        """
        self.__checker_configs.append(config)

    def get_checker_configs(self):
        """
        Process raw config data (from the command line).
        Filter out checker related configuration values
        like unix:Optimistic=true in the command line:
        '-Xanalyzer -analyzer-config -Xanalyzer unix:Optimistic=true'

        Return a list of (checker_name, key, value) tuples.
        """

        checker_config_pattern = r'(?P<checker_name>([^: ]+))\:' \
            r'(?P<checker_attr>([^:=]+))\=(?P<attr_value>([^:\. ]+))'

        raw_config = self.analyzer_extra_arguments
        LOG.debug_analyzer('Analyzer extra args: ' + raw_config)

        checker_configs = re.finditer(checker_config_pattern, raw_config)

        if checker_configs:
            for cfg in checker_configs:
                checker_name = cfg.group('checker_name')
                checker_attr = cfg.group('checker_attr')
                attr_value = cfg.group('attr_value')
                self.__checker_configs.append((checker_name,
                                               checker_attr,
                                               attr_value))
        LOG.debug_analyzer(self.__checker_configs)

        return self.__checker_configs
