# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Context to store package related information.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import os
import sys

from libcodechecker import db_version
from libcodechecker import logger
# TODO: Refers subpackage library
from libcodechecker.analyze.analyzers import analyzer_types

LOG = logger.get_logger('system')


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
        self._codechecker_workspace = None
        self._severity_map = dict()

        self.__package_version = None
        self.__product_db_version_info = None
        self.__run_db_version_info = None
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
        self._package_root = os.environ.get(env_vars['env_package_root'])

        self._codechecker_workspace = os.environ.get('codechecker_workspace')

        try:
            with open(self.checkers_severity_map_file) as severity_file:
                self._severity_map = json.load(severity_file)
        except (IOError, ValueError):
            LOG.warning("{0} doesn't exist or not JSON format. Severity "
                        "levels will not be available!"
                        .format(self.checkers_severity_map_file))

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
        try:
            with open(self.version_file, 'r') as vfile:
                vfile_data = json.loads(vfile.read())

            package_version = vfile_data['version']
            package_build_date = vfile_data['package_build_date']
            package_git_hash = vfile_data['git_hash']
            package_git_tag = vfile_data['git_describe']['tag']
            package_git_dirtytag = vfile_data['git_describe']['dirty']
            product_database_version = vfile_data['product_db_version']
            run_database_version = vfile_data['run_db_version']

            self.__package_version = package_version['major'] + '.' + \
                package_version['minor'] + '.' + \
                package_version['revision']
            self.__product_db_version_info = db_version.DBVersionInfo(
                product_database_version['major'],
                product_database_version['minor'])
            self.__run_db_version_info = db_version.DBVersionInfo(
                run_database_version['major'],
                run_database_version['minor'])

            self.__package_build_date = package_build_date
            self.__package_git_hash = package_git_hash

            self.__package_git_tag = package_git_tag
            if (LOG.getEffectiveLevel() == logger.DEBUG or
                    LOG.getEffectiveLevel() ==
                    logger.DEBUG_ANALYZER):
                self.__package_git_tag = package_git_dirtytag

        except ValueError as verr:
            # db_version is required to know if the db schema is compatible.
            LOG.error('Failed to get version info from the version file.')
            LOG.error(verr)
            sys.exit(1)

        except IOError as ioerr:
            LOG.error('Failed to read version config file: ' +
                      self.version_file)
            LOG.error(ioerr)
            sys.exit(1)

    def __populate_analyzers(self):
        compiler_binaries = self.pckg_layout.get('analyzers')
        if not compiler_binaries:
            # Set default analyzers assume they are in the PATH
            # will be checked later.
            # Key naming in the dict should be the same as in
            # the supported analyzers list.
            self.__analyzers[analyzer_types.CLANG_SA] = 'clang'
            self.__analyzers[analyzer_types.CLANG_TIDY] = 'clang-tidy'
        else:
            for name, value in compiler_binaries.items():
                if os.path.isabs(value):
                    # Check if it is an absolute path.
                    self.__analyzers[name] = value
                elif os.path.dirname(value):
                    # Check if it is a package relative path.
                    self.__analyzers[name] = os.path.join(self._package_root,
                                                          value)
                else:
                    self.__analyzers[name] = value

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
    def product_db_version_info(self):
        return self.__product_db_version_info

    @property
    def run_db_version_info(self):
        return self.__run_db_version_info

    @property
    def version_file(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['version_file'])

    @property
    def env_var_cc_logger_bin(self):
        return self.env_vars['cc_logger_bin']

    @property
    def env_var_ld_preload(self):
        return self.env_vars['ld_preload']

    @property
    def env_var_cc_logger_compiles(self):
        return self.env_vars['cc_logger_compiles']

    @property
    def env_var_cc_logger_file(self):
        return self.env_vars['cc_logger_file']

    @property
    def path_logger_bin(self):
        return os.path.join(self.package_root,
                            self.pckg_layout['ld_logger_bin'])

    @property
    def path_logger_lib(self):
        return os.path.join(self.package_root,
                            self.pckg_layout['ld_logger_lib_path'])

    @property
    def logger_lib_name(self):
        return self.pckg_layout['ld_logger_lib_name']

    @property
    def path_plist_to_html_bin(self):
        return os.path.join(self.package_root,
                            self.pckg_layout['plist_to_html_bin'])

    @property
    def path_plist_to_html_dist(self):
        return os.path.join(self.package_root,
                            self.pckg_layout['plist_to_html_dist_path'])

    @property
    def compiler_resource_dir(self):
        resource_dir = self.pckg_layout.get('compiler_resource_dir')
        if not resource_dir:
            return ""
        else:
            if os.path.isabs(resource_dir):
                return resource_dir
            else:
                return os.path.join(self._package_root, resource_dir)

    @property
    def path_env_extra(self):
        extra_paths = self.pckg_layout.get('path_env_extra')
        if not extra_paths:
            return []
        else:
            paths = []
            for path in extra_paths:
                if os.path.isabs(path):
                    paths.append(path)
                else:
                    paths.append(os.path.join(self._package_root, path))
            return paths

    @property
    def ld_lib_path_extra(self):
        extra_lib = self.pckg_layout.get('ld_lib_path_extra')
        if not extra_lib:
            return []
        else:
            ld_paths = []
            for path in extra_lib:
                if os.path.isabs(path):
                    ld_paths.append(path)
                else:
                    ld_paths.append(os.path.join(self._package_root, path))
            return ld_paths

    @property
    def analyzer_binaries(self):
        return self.__analyzers

    @property
    def ctu_func_map_cmd(self):
        ctu_func_mapping = self.pckg_layout['ctu_func_map_cmd']

        if os.path.dirname(ctu_func_mapping):
            # If it is a relative path, it is by definition relative to
            # the package_root, just like how analyzers are set up.
            ctu_func_mapping = os.path.join(self._package_root,
                                            ctu_func_mapping)

        return ctu_func_mapping

    @property
    def package_root(self):
        return self._package_root

    @property
    def checker_plugin(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['plugin'])

    @property
    def gdb_config_file(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['gdb_config_file'])

    @property
    def checkers_severity_map_file(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['checkers_severity_map_file'])

    @property
    def doc_root(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['docs'])

    @property
    def www_root(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['www'])

    @property
    def run_migration_root(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['run_db_migrate'])

    @property
    def config_migration_root(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['config_db_migrate'])

    @property
    def db_username(self):
        return self._db_username

    @db_username.setter
    def db_username(self, value):
        self._db_username = value

    @property
    def codechecker_workspace(self):
        return self._codechecker_workspace

    @codechecker_workspace.setter
    def codechecker_workspace(self, value):
        self._codechecker_workspace = value

    @property
    def severity_map(self):
        return self._severity_map


def get_context():
    LOG.debug('Loading package config.')

    package_root = os.environ['CC_PACKAGE_ROOT']

    pckg_config_file = os.path.join(package_root, "config", "config.json")
    LOG.debug('Reading config: ' + pckg_config_file)
    with open(pckg_config_file, 'r') as cfg:
        cfg_dict = json.loads(cfg.read())

    LOG.debug(cfg_dict)

    LOG.debug('Loading layout config.')

    layout_cfg_file = os.path.join(package_root, "config",
                                   "package_layout.json")
    LOG.debug(layout_cfg_file)
    with open(layout_cfg_file, 'r') as lcfg:
        lcfg_dict = json.loads(lcfg.read())

    # Merge static and runtime layout.
    layout_config = lcfg_dict['static'].copy()
    layout_config.update(lcfg_dict['runtime'])

    LOG.debug(layout_config)

    try:
        return Context(package_root,
                       layout_config,
                       cfg_dict)

    except KeyError as kerr:
        LOG.error(kerr)
        sys.exit(1)
