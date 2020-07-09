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


from collections.abc import Mapping
# pylint: disable=no-name-in-module
from distutils.spawn import find_executable

import os
import sys

from codechecker_common import logger
from codechecker_common.util import load_json_or_empty

from . import env

LOG = logger.get_logger('system')


class SeverityMap(Mapping):
    """
    A dictionary which maps checker names to severity levels.
    If a key is not found in the map then it will return MEDIUM severity in
    case of compiler warnings and CRITICAL in case of compiler errors.
    """

    def __init__(self, *args, **kwargs):
        self.store = dict(*args, **kwargs)

    def __getitem__(self, key):
        # Key is not specified in the store and it is a compiler warning
        # or error.
        if key not in self.store:
            if key == 'clang-diagnostic-error':
                return "CRITICAL"
            elif key.startswith('clang-diagnostic-'):
                return "MEDIUM"

        return self.store[key] if key in self.store else 'UNSPECIFIED'

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


class GuidelineMap(Mapping):
    def __init__(self, guideline_map_file):
        self.store = load_json_or_empty(guideline_map_file, {})
        self.__check_json_format(guideline_map_file)

    def __check_json_format(self, guideline_map_file):
        """
        This function checks the format of checker_guideline_map.json config
        file. If this config file doesn't meet the requirements, then
        CodeChecker exits with status 1.

        {
          "guidelines": {
            "guideline_1": "url_1",
            "guideline_2": "url_2"
          },
          "mapping": {
            "checker_1": {
              "guideline_1": ["id_1", "id_2"]
            }
          }
        }

        "guidelines" and "mapping" attributes are mandatory, the list of IDs
        must be a list, and the guideline name must be enumerated at
        "guidelines" attribute
        """
        if 'guidelines' not in self.store:
            LOG.error('Format error in %s: "guideline" key not found',
                      guideline_map_file)
            sys.exit(1)
        if 'mapping' not in self.store:
            LOG.error('Format error in %s: "mapping" key not found',
                      guideline_map_file)
            sys.exit(1)

        for checker, guidelines in self.store['mapping'].items():
            if not isinstance(guidelines, dict):
                LOG.error('Format error in %s: value of %s must be a '
                          'dictionary', guideline_map_file, checker)
                sys.exit(1)

            diff = set(guidelines) - set(self.store['guidelines'])
            if diff:
                LOG.error('Format error in %s: %s at %s not documented under '
                          '"guidelines"',
                          guideline_map_file, ', '.join(diff), checker)
                sys.exit(1)

            for guideline, ids in guidelines.items():
                if not isinstance(ids, list):
                    LOG.error('Format error in %s: value of %s at checker %s '
                              'must be a list',
                              guideline_map_file, guideline, checker)
                    sys.exit(1)

    def __getitem__(self, key):
        return self.store['mapping'][key]

    def __iter__(self):
        return iter(self.store['mapping'])

    def __len__(self):
        return len(self.store)


# -----------------------------------------------------------------------------
class Context(object):
    """ Generic package specific context. """

    def __init__(self, package_root, pckg_layout, cfg_dict):
        env_vars = cfg_dict['environment_variables']
        self.__checker_config = cfg_dict['checker_config']
        self.__available_profiles = cfg_dict['available_profiles']

        # Get the common environment variables.
        self.pckg_layout = pckg_layout
        self.env_vars = env_vars

        self._package_root = package_root
        self._severity_map = SeverityMap(
            load_json_or_empty(self.checkers_severity_map_file, {}))
        self._guideline_map = GuidelineMap(self.checkers_guideline_map_file)
        self.__package_version = None
        self.__package_build_date = None
        self.__package_git_hash = None
        self.__analyzers = {}

        self.logger_bin = None
        self.logger_file = None
        self.logger_compilers = None

        # Get package specific environment variables.
        self.set_env(env_vars)

        self.__set_version()
        self.__populate_analyzers()

    def set_env(self, env_vars):
        """
        Get the environment variables.
        """
        # Get generic package specific environment variables.
        self.logger_bin = os.environ.get(env_vars['cc_logger_bin'])
        self.logger_file = os.environ.get(env_vars['cc_logger_file'])
        self.logger_compilers = os.environ.get(env_vars['cc_logger_compiles'])
        self.ld_preload = os.environ.get(env_vars['ld_preload'])
        self.ld_lib_path = env_vars['env_ld_lib_path']

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
                self.__analyzers[name] = os.path.join(self._package_root,
                                                      value)
            else:
                env_path = analyzer_env['PATH'] if analyzer_env else None
                compiler_binary = find_executable(value, env_path)
                if not compiler_binary:
                    LOG.warning("'%s' binary can not be found in your PATH!",
                                value)
                    continue

                self.__analyzers[name] = os.path.realpath(compiler_binary)

    @property
    def checker_config(self):
        return self.__checker_config

    @property
    def available_profiles(self):
        return self.__available_profiles

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
        return os.path.join(self._package_root, 'config',
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
        return os.path.join(self.package_root, 'bin', 'ld_logger')

    @property
    def path_logger_lib(self):
        return os.path.join(self.package_root, 'ld_logger', 'lib')

    @property
    def logger_lib_name(self):
        return 'ldlogger.so'

    @property
    def path_plist_to_html_dist(self):
        return os.path.join(self.package_root, 'lib', 'python3',
                            'plist_to_html', 'static')

    @property
    def compiler_resource_dir(self):
        resource_dir = self.pckg_layout.get('compiler_resource_dir')
        if not resource_dir:
            return ""
        return os.path.join(self._package_root, resource_dir)

    @property
    def path_env_extra(self):
        if env.is_analyzer_from_path():
            return []

        extra_paths = self.pckg_layout.get('path_env_extra', [])
        paths = []
        for path in extra_paths:
            paths.append(os.path.join(self._package_root, path))
        return paths

    @property
    def ld_lib_path_extra(self):
        if env.is_analyzer_from_path():
            return []

        extra_lib = self.pckg_layout.get('ld_lib_path_extra', [])
        ld_paths = []
        for path in extra_lib:
            ld_paths.append(os.path.join(self._package_root, path))
        return ld_paths

    @property
    def analyzer_binaries(self):
        return self.__analyzers

    @property
    def package_root(self):
        return self._package_root

    @property
    def checker_plugin(self):
        # Do not load the plugin because it might be incompatible.
        if env.is_analyzer_from_path():
            return None

        return os.path.join(self._package_root, 'plugin')

    @property
    def checkers_severity_map_file(self):
        """
        Returns the path of checker-severity mapping config file. This file
        may come from a custom location provided by CC_SEVERITY_MAP_FILE
        environment variable.
        """
        # Get severity map file from the environment.
        if 'CC_SEVERITY_MAP_FILE' in os.environ:
            severity_map_file = os.environ.get('CC_SEVERITY_MAP_FILE')

            LOG.warning("Severity map file set through the "
                        "'CC_SEVERITY_MAP_FILE' environment variable: %s",
                        severity_map_file)

            return severity_map_file

        return os.path.join(self._package_root, 'config',
                            'checker_severity_map.json')

    @property
    def checkers_guideline_map_file(self):
        """
        Returns the path of checker-guideline mapping config file. This file
        may come from a custom location provided by CC_GUIDELINE_MAP_FILE
        environment variable.
        """
        # Get coding guideline map file from the environment.
        if 'CC_GUIDELINE_MAP_FILE' in os.environ:
            guideline_map_file = os.environ.get('CC_GUIDELINE_MAP_FILE')

            LOG.warning("Coding guideline map file set through the "
                        "'CC_GUIDELINE_MAP_FILE' environment variable: %s",
                        guideline_map_file)

            return guideline_map_file

        return os.path.join(self._package_root, 'config',
                            'checker_guideline_map.json')

    @property
    def severity_map(self):
        return self._severity_map

    @property
    def guideline_map(self):
        return self._guideline_map


def get_context():
    LOG.debug('Loading package config.')

    package_root = os.environ['CC_PACKAGE_ROOT']

    pckg_config_file = os.path.join(package_root, "config", "config.json")
    LOG.debug('Reading config: %s', pckg_config_file)
    cfg_dict = load_json_or_empty(pckg_config_file)

    if not cfg_dict:
        sys.exit(1)

    LOG.debug(cfg_dict)

    LOG.debug('Loading layout config.')

    layout_cfg_file = os.path.join(package_root, "config",
                                   "package_layout.json")
    LOG.debug(layout_cfg_file)
    lcfg_dict = load_json_or_empty(layout_cfg_file)

    if not lcfg_dict:
        sys.exit(1)

    try:
        return Context(package_root, lcfg_dict['runtime'], cfg_dict)
    except KeyError:
        import traceback
        traceback.print_exc()
        sys.exit(1)
