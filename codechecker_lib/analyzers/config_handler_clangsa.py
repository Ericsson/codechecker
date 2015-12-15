# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import re
import StringIO

from codechecker_lib.analyzers import config_handler


class ClangSAConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for the clang static analyzer
    """

    def __init__(self, config_data):
        super(ClangSAConfigHandler, self).__init__(config_data)

        # list of (True/False, checker_name) tuples where order matters!
        self.__checks = []

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

    def get_configs(self):
        """
        return a lis of tuples
        """
        configs = []
        checker_name = ''

        for line in self.config_data.split('\n'):
            result = re.match('^\[(.*)\]$', line)
            if result:
                checker_name = result.group(1)
            else:
                result = re.match('^(.*)=(.*)$', line)
                if result:
                    key = result.group(1)
                    key_value = result.group(2)
                    configs.append((checker_name, key, key_value))

        return configs
