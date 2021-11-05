# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Context to store package related information.
"""


# pylint: disable=no-name-in-module
from distutils.spawn import find_executable

import os
import sys

from codechecker_report_converter.util import load_json_or_empty

from codechecker_common import logger
from codechecker_common.checker_labels import CheckerLabels
from codechecker_common.singleton import Singleton

from . import env

LOG = logger.get_logger('system')


# -----------------------------------------------------------------------------
class Context(metaclass=Singleton):
    """ Generic package specific context. """

    def __init__(self):
        """ Initialize analyzer context. """
        self._bin_dir_path = os.environ.get('CC_BIN_DIR', '')
        self._lib_dir_path = os.environ.get('CC_LIB_DIR', '')
        self._data_files_dir_path = os.environ.get('CC_DATA_FILES_DIR', '')

        # Use this environment variable for testing purposes only. This
        # variable helps to configure which labels to use in this context.
        labels_dir = os.path.join(self._data_files_dir_path,
                                  'config', 'labels')
        if 'CC_TEST_LABELS_DIR' in os.environ:
            labels_dir = os.environ['CC_TEST_LABELS_DIR']

        cfg_dict = self.__get_package_config()
        self.env_vars = cfg_dict['environment_variables']

        lcfg_dict = self.__get_package_layout()
        self.pckg_layout = lcfg_dict['runtime']

        self._checker_labels = CheckerLabels(labels_dir)
        self.__package_version = None
        self.__package_build_date = None
        self.__package_git_hash = None
        self.__analyzers = {}

        self.logger_lib_dir_path = os.path.join(
            self._data_files_dir_path, 'ld_logger', 'lib')

        if not os.path.exists(self.logger_lib_dir_path):
            self.logger_lib_dir_path = os.path.join(
                self._lib_dir_path, 'codechecker_analyzer', 'ld_logger', 'lib')

        self.logger_bin = None
        self.logger_file = None
        self.logger_compilers = None

        # Init package specific environment variables.
        self.__init_env()

        self.__set_version()
        self.__populate_analyzers()
        self.__populate_replacer()

    def __get_package_config(self):
        """ Get package configuration. """
        pckg_config_file = os.path.join(
            self._data_files_dir_path, "config", "config.json")

        LOG.debug('Reading config: %s', pckg_config_file)
        cfg_dict = load_json_or_empty(pckg_config_file)

        if not cfg_dict:
            raise ValueError(f"No configuration file '{pckg_config_file}' can "
                             f"be found or it is empty!")

        LOG.debug(cfg_dict)
        return cfg_dict

    def __get_package_layout(self):
        """ Get package layout configuration. """
        layout_cfg_file = os.path.join(
            self._data_files_dir_path, "config", "package_layout.json")

        LOG.debug('Reading config: %s', layout_cfg_file)
        lcfg_dict = load_json_or_empty(layout_cfg_file)

        if not lcfg_dict:
            raise ValueError(f"No configuration file '{layout_cfg_file}' can "
                             f"be found or it is empty!")

        return lcfg_dict

    def __init_env(self):
        """ Set environment variables. """
        # Get generic package specific environment variables.
        self.logger_bin = os.environ.get(self.env_vars['cc_logger_bin'])
        self.logger_file = os.environ.get(self.env_vars['cc_logger_file'])
        self.logger_compilers = os.environ.get(
            self.env_vars['cc_logger_compiles'])
        self.ld_preload = os.environ.get(self.env_vars['ld_preload'])
        self.ld_lib_path = self.env_vars['env_ld_lib_path']

    def __set_version(self):
        """
        Get the package version from the version config file.
        """
        vfile_data = load_json_or_empty(self.version_file)

        if not vfile_data:
            sys.exit(1)

        package_version = vfile_data['version']
        package_build_date = vfile_data['package_build_date']
        package_git_hash = vfile_data.get('git_hash')
        package_git_tag = vfile_data.get('git_describe', {}).get('tag')
        package_git_dirtytag = vfile_data.get('git_describe', {}).get('dirty')

        self.__package_version = package_version['major'] + '.' + \
            package_version['minor'] + '.' + \
            package_version['revision']

        self.__package_build_date = package_build_date
        self.__package_git_hash = package_git_hash

        self.__package_git_tag = package_git_tag
        if (LOG.getEffectiveLevel() == logger.DEBUG or
                LOG.getEffectiveLevel() ==
                logger.DEBUG_ANALYZER):
            self.__package_git_tag = package_git_dirtytag

    def __populate_analyzers(self):
        """ Set analyzer binaries for each registered analyzers. """
        analyzer_env = None
        analyzer_from_path = env.is_analyzer_from_path()
        if not analyzer_from_path:
            analyzer_env = env.extend(self.path_env_extra,
                                      self.ld_lib_path_extra)

        compiler_binaries = self.pckg_layout.get('analyzers')
        for name, value in compiler_binaries.items():

            if analyzer_from_path:
                value = os.path.basename(value)

            if os.path.dirname(value):
                # Check if it is a package relative path.
                self.__analyzers[name] = os.path.join(
                    self._data_files_dir_path, value)
            else:
                env_path = analyzer_env['PATH'] if analyzer_env else None
                compiler_binary = find_executable(value, env_path)
                if not compiler_binary:
                    LOG.debug("'%s' binary can not be found in your PATH!",
                              value)
                    continue

                self.__analyzers[name] = os.path.realpath(compiler_binary)

                # If the compiler binary is a simlink to ccache, use the
                # original compiler binary.
                if self.__analyzers[name].endswith("/ccache"):
                    self.__analyzers[name] = compiler_binary

    def __populate_replacer(self):
        """ Set clang-apply-replacements tool. """
        replacer_binary = self.pckg_layout.get('clang-apply-replacements')

        if os.path.dirname(replacer_binary):
            # Check if it is a package relative path.
            self.__replacer = os.path.join(self._data_files_dir_path,
                                           replacer_binary)
        else:
            self.__replacer = find_executable(replacer_binary)

    @property
    def version(self):
        return self.__package_version

    @property
    def package_build_date(self):
        return self.__package_build_date

    @property
    def package_git_hash(self):
        return self.__package_git_hash

    @property
    def package_git_tag(self):
        return self.__package_git_tag

    @property
    def version_file(self):
        return os.path.join(self._data_files_dir_path, 'config',
                            'analyzer_version.json')

    @property
    def env_var_cc_logger_bin(self):
        return self.env_vars['cc_logger_bin']

    @property
    def env_var_ld_preload(self):
        return self.env_vars['ld_preload']

    @property
    def env_var_cc_logger_file(self):
        return self.env_vars['cc_logger_file']

    @property
    def path_logger_bin(self):
        return os.path.join(self._bin_dir_path, 'ld_logger')

    @property
    def path_logger_lib(self):
        return self.logger_lib_dir_path

    @property
    def logger_lib_name(self):
        return 'ldlogger.so'

    @property
    def path_plist_to_html_dist(self):
        return os.path.join(self._lib_dir_path, 'codechecker_report_converter',
                            'report', 'output', 'html', 'static')

    @property
    def path_env_extra(self):
        if env.is_analyzer_from_path():
            return []

        extra_paths = self.pckg_layout.get('path_env_extra', [])
        paths = []
        for path in extra_paths:
            paths.append(os.path.join(self._data_files_dir_path, path))
        return paths

    @property
    def ld_lib_path_extra(self):
        if env.is_analyzer_from_path():
            return []

        extra_lib = self.pckg_layout.get('ld_lib_path_extra', [])
        ld_paths = []
        for path in extra_lib:
            ld_paths.append(os.path.join(self._data_files_dir_path, path))
        return ld_paths

    @property
    def analyzer_binaries(self):
        return self.__analyzers

    @property
    def replacer_binary(self):
        return self.__replacer

    @property
    def data_files_dir_path(self):
        return self._data_files_dir_path

    @property
    def checker_plugin(self):
        # Do not load the plugin because it might be incompatible.
        if env.is_analyzer_from_path():
            return None

        return os.path.join(self._data_files_dir_path, 'plugin')

    @property
    def checker_labels(self):
        return self._checker_labels


def get_context():
    try:
        return Context()
    except KeyError:
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except ValueError as err:
        LOG.error(err)
        sys.exit(1)
