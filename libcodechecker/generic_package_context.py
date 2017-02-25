# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import json
import os
import sys

from codechecker_lib import context_base
from codechecker_lib import db_version
from codechecker_lib import logger
from codechecker_lib.analyzers import analyzer_types

LOG = logger.LoggerFactory.get_new_logger('CONTEXT')


# -----------------------------------------------------------------------------
class Context(context_base.ContextBase):
    """ Generic package specific context. """

    __instance = None

    logger_bin = None
    logger_file = None
    logger_compilers = None
    ld_preload = None
    __package_version = None
    __package_root = None

    def __init__(self, package_root, pckg_layout, cfg_dict):

        env_vars = cfg_dict['environment_variables']
        variables = cfg_dict['package_variables']
        self.__checker_config = cfg_dict['checker_config']

        # Base class constructor gets the common environment variables.
        super(Context, self).__init__()
        super(Context, self).load_data(env_vars, pckg_layout, variables)

        # Get package specific environment variables.
        self.set_env(env_vars)

        self.__package_root = package_root

        self.__package_version = None
        self.__db_version_info = None
        self.__package_build_date = None
        self.__package_git_hash = None

        self.__set_version()

        Context.__instance = self

    def set_env(self, env_vars):
        """
        Get the environment variables.
        """
        super(Context, self).set_env(env_vars)

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
            database_version = vfile_data['db_version']

            self.__package_version = package_version['major'] + '.' + \
                package_version['minor'] + '.' + \
                package_version['revision']
            self.__db_version_info = db_version.DBVersionInfo(
                database_version['major'],
                database_version['minor'])

            self.__package_build_date = package_build_date
            self.__package_git_hash = package_git_hash

            self.__package_git_tag = package_git_tag
            if (logger.LoggerFactory.get_log_level() == logger.DEBUG or
                    logger.LoggerFactory.get_log_level() ==
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

    @property
    def default_checkers_config(self):
        return self.__checker_config

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
    def db_version_info(self):
        return self.__db_version_info

    @property
    def version_file(self):
        return os.path.join(self.__package_root,
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
    def dumps_dir_name(self):
        return self.variables['path_dumps_name']

    @property
    def pg_data_dir(self):
        return os.path.join(self.codechecker_workspace,
                            self.pgsql_data_dir_name)

    @property
    def dump_output_dir(self):
        return os.path.join(self.codechecker_workspace,
                            self.variables['path_dumps_name'])

    @property
    def compiler_resource_dir(self):
        resource_dir = self.pckg_layout.get('compiler_resource_dir')
        if not resource_dir:
            return ""
        else:
            if os.path.isabs(resource_dir):
                return resource_dir
            else:
                return os.path.join(self.__package_root, resource_dir)

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
                    paths.append(os.path.join(self.__package_root, path))
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
                    ld_paths.append(os.path.join(self.__package_root, path))
            return ld_paths

    @property
    def analyzer_binaries(self):
        analyzers = {}

        compiler_binaries = self.pckg_layout.get('analyzers')
        if not compiler_binaries:
            # Set default analyzers assume they are in the PATH
            # will be checked later.
            # Key naming in the dict should be the same as in
            # the supported analyzers list.
            analyzers[analyzer_types.CLANG_SA] = 'clang'
            analyzers[analyzer_types.CLANG_TIDY] = 'clang-tidy'
        else:
            for name, value in compiler_binaries.items():
                if os.path.isabs(value):
                    # Check if it is an absolute path.
                    analyzers[name] = value
                elif os.path.dirname(value):
                    # Check if it is a package relative path.
                    analyzers[name] = os.path.join(self.__package_root, value)
                else:
                    analyzers[name] = value

        return analyzers


def get_context():
    LOG.debug('Loading package config.')

    package_root = os.environ['CC_PACKAGE_ROOT']

    pckg_config_file = os.path.join(package_root, "config", "config.json")
    LOG.debug('Reading config: ' + pckg_config_file)
    with open(pckg_config_file, 'r') as cfg:
        cfg_dict = json.loads(cfg.read())

    LOG.debug(cfg_dict)

    LOG.debug('Loading layout config')

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
