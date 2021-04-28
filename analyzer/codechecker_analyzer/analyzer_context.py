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
from codechecker_common.singleton import Singleton
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

        return self.store.get(key, 'UNSPECIFIED')

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


class ProfileMap(Mapping):
    """
    A dictionary which maps checker names and checker groups to profile names.
    A checker or checker group may be the member of multiple profiles.
    """
    def __init__(self, profile_map_file):
        self.store = load_json_or_empty(profile_map_file, {})
        self.__check_json_format(profile_map_file)

    def __check_json_format(self, profile_map_file):
        """
        This function checks the format of the given profile map config file.
        If this file doesn't meet the requirements, then CodeChecker exits with
        status 1.

        {
          "available_profiles": {
            "profile1": "description1",
            "profile2": "description2"
          },
          "analyzers": {
            "analyzer1": {
              "profile1": ['checker1', 'checker2']
            },
            "analyzer2": {
              "profile1": ['checker3'],
              "profile2": ['checker3', 'checker4']
            }
          }
        }
        """
        if 'available_profiles' not in self.store:
            raise ValueError(f'Format error in {profile_map_file}: '
                             '"available_profiles" key not found')
        if 'analyzers' not in self.store:
            raise ValueError(f'Format error in {profile_map_file}: '
                             '"analyzers" key not found')

        for analyzer, profiles in self.store['analyzers'].items():
            if not isinstance(profiles, dict):
                raise ValueError(f'Format error in {profile_map_file}: '
                                 f'value of {analyzer} must be a dictionary')

            diff = set(profiles) - set(self.store['available_profiles'])
            if diff:
                raise ValueError(f'Format error in {profile_map_file}: '
                                 f'{", ".join(diff)} at {analyzer} not '
                                 'documented under "available_profiles"')

            for profile, checkers in profiles.items():
                if not isinstance(checkers, list):
                    raise ValueError(f'Format error in {profile_map_file}: '
                                     f'value of {profile} at analyzer '
                                     f'{analyzer} must be a list')

    def __getitem__(self, key):
        """
        Returns the list of profiles to which the given checker name or group
        belongs.
        """
        result = []
        for profiles in self.store['analyzers'].values():
            for profile, checkers in profiles.items():
                if any(key.startswith(checker) for checker in checkers):
                    result.append(profile)
        return result

    def __iter__(self):
        """
        This mapping class maps checker groups/names to profiles. However,
        since not every checkers are listed necessarily in the profile config
        file, we can't iterate over them. Still, we map checkers to profiles
        and not in reverse, because we want to be consistent with the other
        mapping classes.
        """
        raise NotImplementedError("Can't iterate profiles by checkers.")

    def __len__(self):
        """
        Not implemented for the same reason as __iter__() is not implemented.
        """
        raise NotImplementedError("Can't determine the number of checkers")

    def by_profile(self, profile, analyzer_tool=None):
        """
        Return checkers of a given profile. Optionally an analyzer tool name
        can be given.
        """
        result = []
        for analyzer, profiles in self.store['analyzers'].items():
            if analyzer_tool is None or analyzer == analyzer_tool:
                result.extend(profiles.get(profile, []))
        return result

    def available_profiles(self):
        """
        Returns the dict of available profiles and their descriptions. The
        config file may contain profile groups of several analyzers. It is
        possible that some analyzer doesn't contain checkers of a specific
        profile.
        """
        return self.store['available_profiles']


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
            raise ValueError(f'Format error in {guideline_map_file}: '
                             '"guideline" key not found')
        if 'mapping' not in self.store:
            raise ValueError(f'Format error in {guideline_map_file}: '
                             '"mapping" key not found')

        for checker, guidelines in self.store['mapping'].items():
            if not isinstance(guidelines, dict):
                raise ValueError(f'Format error in {guideline_map_file}: '
                                 f'value of {checker} must be a dictionary')

            diff = set(guidelines) - set(self.store['guidelines'])
            if diff:
                raise ValueError(f'Format error in {guideline_map_file}: '
                                 f'{", ".join(diff)} at {checker} not '
                                 'documented under "guidelines"')

            for guideline, ids in guidelines.items():
                if not isinstance(ids, list):
                    raise ValueError(f'Format error in {guideline_map_file}: '
                                     f'value of {guideline} at checker '
                                     f'{checker} must be a list')

    def __getitem__(self, key):
        return self.store['mapping'][key]

    def __iter__(self):
        return iter(self.store['mapping'])

    def __len__(self):
        return len(self.store)

    def by_guideline(self, guideline):
        """
        Return checkers belonging to a specific guideline. A checker belongs to
        a guideline if it reports on at least one guideline rule.
        """
        result = []
        for checker, guidelines in self.store['mapping'].items():
            if guideline in guidelines and guidelines[guideline]:
                result.append(checker)
        return result

    def by_rule(self, rule):
        """
        Return checkers belonging to a specific guideline rule.
        """
        result = []
        for checker, guidelines in self.store['mapping'].items():
            if any(rule in rules for _, rules in guidelines.iter()):
                result.append(checker)
        return result

    def available_guidelines(self):
        """
        Returns the dict of available guidelines and their documentations'
        URLs.  It is possible that a guideline is not covered by any checkers.
        """
        return self.store['guidelines']


# -----------------------------------------------------------------------------
class Context(metaclass=Singleton):
    """ Generic package specific context. """

    def __init__(self):
        """ Initialize analyzer context. """
        self._bin_dir_path = os.environ.get('CC_BIN_DIR', '')
        self._lib_dir_path = os.environ.get('CC_LIB_DIR', '')
        self._data_files_dir_path = os.environ.get('CC_DATA_FILES_DIR', '')

        cfg_dict = self.__get_package_config()
        self.env_vars = cfg_dict['environment_variables']

        lcfg_dict = self.__get_package_layout()
        self.pckg_layout = lcfg_dict['runtime']

        self._severity_map = SeverityMap(
            load_json_or_empty(self.checker_severity_map_file, {}))
        self._guideline_map = GuidelineMap(self.checker_guideline_map_file)
        self._profile_map = ProfileMap(self.checker_profile_map_file)
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
        return os.path.join(self._lib_dir_path, 'plist_to_html', 'static')

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
    def checker_severity_map_file(self):
        """
        Returns the path of checker-severity mapping config file. This file
        may come from a custom location provided by CC_SEVERITY_MAP_FILE
        environment variable.
        """
        # Get severity map file from the environment.
        severity_map_file = os.environ.get('CC_SEVERITY_MAP_FILE')
        if severity_map_file:
            LOG.warning("Severity map file set through the "
                        "'CC_SEVERITY_MAP_FILE' environment variable: %s",
                        severity_map_file)

            return severity_map_file

        return os.path.join(self._data_files_dir_path, 'config',
                            'checker_severity_map.json')

    @property
    def checker_guideline_map_file(self):
        """
        Returns the path of checker-guideline mapping config file. This file
        may come from a custom location provided by CC_GUIDELINE_MAP_FILE
        environment variable.
        """
        # Get coding guideline map file from the environment.
        guideline_map_file = os.environ.get('CC_GUIDELINE_MAP_FILE')
        if guideline_map_file:
            LOG.warning("Coding guideline map file set through the "
                        "'CC_GUIDELINE_MAP_FILE' environment variable: %s",
                        guideline_map_file)

            return guideline_map_file

        return os.path.join(self._data_files_dir_path, 'config',
                            'checker_guideline_map.json')

    @property
    def checker_profile_map_file(self):
        """
        Returns the path of checker-profile mapping config file. This file
        may come from a custom location provided by CC_PROFILE_MAP_FILE
        environment variable.
        """
        # Get profile map file from the environment.
        profile_map_file = os.environ.get('CC_PROFILE_MAP_FILE')
        if profile_map_file:
            LOG.warning("Profile map file set through the "
                        "'CC_PROFILE_MAP_FILE' environment variable: %s",
                        profile_map_file)

            return profile_map_file

        return os.path.join(self._data_files_dir_path, 'config',
                            'checker_profile_map.json')

    @property
    def severity_map(self):
        return self._severity_map

    @property
    def guideline_map(self):
        return self._guideline_map

    @property
    def profile_map(self):
        return self._profile_map


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
