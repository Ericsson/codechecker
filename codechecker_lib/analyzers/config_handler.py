# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os

from abc import ABCMeta, abstractmethod

from codechecker_lib import logger

LOG = logger.get_new_logger('CONFIG HANDLER')

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
