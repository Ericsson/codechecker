# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import re
import StringIO

from codechecker_lib import logger

from codechecker_lib.analyzers import config_handler

LOG = logger.get_new_logger('CLANGSA CONFIG HANDLER')

class ClangSAConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for the clang static analyzer

    """

    def __init__(self):
        super(ClangSAConfigHandler, self).__init__()

        # list of (True/False, checker_name) tuples where order matters!
        self.__checks = []
        self.__checker_configs = []

    def set_checks(self, checks):
        self.__checks = checks

    def add_checks(self, checks):
        self.__checks.extend(checks)

    def checks(self):
        """
        list of (True/False, checker_name) tuples where order matters!
        """
        return self.__checks

    def checks_str(self):
        """
        return the checkers formatted for printing
        """
        output = StringIO.StringIO()
        output.write('Default checkers set for Clang Static Analyzer:\n')
        output.write('-----------------------------------------------\n')
        output.write('Enabled:\n')
        # enabled checkers
        enabled_checkers = filter(lambda x: x[1], self.__checks)
        for checker_name, _ in enabled_checkers:
            output.write('  ' + checker_name + '\n')

        output.write('')

        # disabled checkers
        output.write('Disabled:\n')
        disabled_checkers = filter(lambda x: not x[1], self.__checks)
        for checker_name, _ in disabled_checkers:
            output.write('  ' + checker_name + '\n')

        res = output.getvalue()
        output.close()
        return res

    def add_checker_config(self, config):
        """
        add a (checker_name, key, value) tuple to the list
        """
        self.__checker_configs.append(config)

    def get_checker_configs(self):
        """
        Process raw config data (from the command line)
        Filter out checker related configuration values
        like unix:Optimistic=true in the command line:
        '-Xanalyzer -analyzer-config -Xanalyzer unix:Optimistic=true'

        return a list of (checker_name, key, value) tuples
        """

        checker_config_pattern = r'(?P<checker_name>([^: ]+))\:(?P<checker_attr>([^:=]+))\=(?P<attr_value>([^:\. ]+))'

        raw_config = self.analyzer_extra_arguments
        LOG.debug(raw_config)

        checker_configs = re.finditer(checker_config_pattern, raw_config)

        if checker_configs:
            for cfg in checker_configs:
                checker_name = cfg.group('checker_name')
                checker_attr = cfg.group('checker_attr')
                attr_value = cfg.group('attr_value')
                self.__checker_configs.append((checker_name,
                                               checker_attr,
                                               attr_value))
        LOG.debug(self.__checker_configs)

        return self.__checker_configs
