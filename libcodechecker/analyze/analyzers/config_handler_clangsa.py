# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import re

from libcodechecker.analyze.analyzers import config_handler
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('CLANGSA CONFIG HANDLER')


class ClangSAConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for the clang static analyzer.
    """

    def __init__(self):
        super(ClangSAConfigHandler, self).__init__()
        self.__checker_configs = []
        self.__ctu_dir = ''
        self.__ctu_in_memory = False
        self.__log_file = ''

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

    @property
    def ctu_dir(self):
        return self.__ctu_dir

    @ctu_dir.setter
    def ctu_dir(self, value):
        self.__ctu_dir = value

    @property
    def ctu_in_memory(self):
        return self.__ctu_in_memory

    @ctu_in_memory.setter
    def ctu_in_memory(self, value):
        self.__ctu_in_memory = value

    @property
    def log_file(self):
        return self.__log_file

    @log_file.setter
    def log_file(self, value):
        self.__log_file = value
