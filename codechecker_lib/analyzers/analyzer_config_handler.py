# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import re
import json
import StringIO

from abc import ABCMeta, abstractmethod

from codechecker_lib import logger

LOG = logger.get_new_logger('ANALYZER_CONFIG_HANDLER')

class AnalyzerConfigHandler(object):
    """
    handle the checker configurations
    and enabled disabled checkers lists
    """
    __metaclass__ = ABCMeta

    def __init__(self, config_data):

        self.__config_data = config_data
        self.__analyzer_binary = None
        self.__analyzer_plugins_dir = None
        self.__compiler_sysroot = None
        self.__compiler_resource_dirs = []
        self.__sys_inc = []
        self.__includes = []

    @property
    def analyzer_plugins_dir(self):
        """
        set the directory where shared objects with checkers should be loaded
        """
        return self.__analyzer_plugins_dir

    @analyzer_plugins_dir.setter
    def analyzer_plugins_dir(self, value):
        """
        set the directory where shared objects with checkers should be loaded
        """
        self.__analyzer_plugins_dir = value

    @property
    def analyzer_plugins(self):
        """
        set the directory where shared objects with checkers should be loaded
        """
        plugin_dir = self.__analyzer_plugins_dir
        analyzer_plugins = [os.path.join(plugin_dir, f)
                            for f in os.listdir(plugin_dir)
                            if os.path.isfile(os.path.join(plugin_dir, f))]
        return analyzer_plugins

    @property
    def analyzer_binary(self):
        return self.__analyzer_binary

    @analyzer_binary.setter
    def analyzer_binary(self, value):
        self.__analyzer_binary = value

    @property
    def config_data(self):
        """
        return the raw config data
        """
        return self.__config_data

    @abstractmethod
    def get_configs(self):
        """
        return a lis of (checker_name, key, key_valye) tuples
        which can be stored to the database
        """
        pass

    @abstractmethod
    def set_checks(self, value):
        """
        set/overwrite the checkers
        """
        pass

    @abstractmethod
    def add_checks(self, checks):
        """
        add additional checkers
        """
        pass

    @abstractmethod
    def checks(self):
        """
        return the checkers
        """
        pass

    @abstractmethod
    def checks_str(self):
        """
        return the checkers formatted for printing
        """
        pass

    @property
    def compiler_sysroot(self):
        """
        get compiler sysroot
        """
        return self.__compiler_sysroot

    @compiler_sysroot.setter
    def compiler_sysroot(self, compiler_sysroot):
        """
        set compiler sysroot
        """
        self.__compiler_sysroot = compiler_sysroot

    @property
    def compiler_resource_dirs(self):
        """
        set compiler resource directories
        """
        return self.__compiler_resource_dirs

    @compiler_resource_dirs.setter
    def compiler_resource_dirs(self, resource_dirs):
        """
        set compiler resource directories
        """
        self.__compiler_resource_dirs = resource_dirs

    @property
    def system_includes(self):
        """
        """
        return self.__sys_inc

    @system_includes.setter
    def system_includes(self, includes):
        """
        """
        self.__sys_inc = includes

    def add_system_includes(self, sys_inc):
        """
        add additional system includes if needed
        """
        self.__sys_inc.append(sys_inc)

    @property
    def includes(self):
        """
        add additional includes if needed
        """
        return self.__includes

    @includes.setter
    def includes(self, includes):
        """
        add additional includes if needed
        """
        self.__includes = includes

    def add_includes(self, inc):
        """
        add additional include paths
        """
        self.__includes.append(inc)


class ClangSAConfigHandler(AnalyzerConfigHandler):
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


class ClangTidyConfigHandler(AnalyzerConfigHandler):
    '''
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
        self.__checks = self.__checks+','+checks

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
        pass
