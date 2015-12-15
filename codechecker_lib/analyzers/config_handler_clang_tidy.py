# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import StringIO

from codechecker_lib.analyzers import config_handler


class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    '''
    Configuration handler for Clang-tidy analyzer
    '''

    def __init__(self, config_data):
        super(ClangTidyConfigHandler, self).__init__(config_data)
        # disable by default enabled checks in clang tidy
        self.__checks = '-*'

    def set_checks(self, checks):
        """
        simple string
        """
        self.__checks = checks

    def add_checks(self, checks):
        """
        """
        if checks != '':
            self.__checks = self.__checks + ',' + checks

    def checks(self):
        """
        """
        return self.__checks

    def checks_str(self):
        """
        return the checkers formatted for printing
        """
        output = StringIO.StringIO()
        output.write('Default checkers set for Clang Tidy:\n')
        output.write('------------------------------------\n')
        output.write(self.__checks)
        res = output.getvalue()
        output.close()
        return res

    def get_configs(self):
        """
        return a lis of tuples
        (checker_name, key, key_value) list
        """
        #TODO implement
        return ''
