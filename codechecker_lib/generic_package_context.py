# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import sys
import json

from codechecker_lib import context_base
from codechecker_lib import logger
from codechecker_lib import db_version

LOG = logger.get_new_logger('CONTEXT')


# -----------------------------------------------------------------------------
class Context(context_base.ContextBase):
    ''' generic package specific context'''

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

        # Base class constructor gets the common environment variables
        super(Context, self).__init__()
        super(Context, self).load_data(env_vars, pckg_layout, variables)

        # get package specific environment variables
        self.set_env(env_vars)

        self.__package_root = package_root

        version, database_version = self.__get_version(self.version_file)
        self.__package_version = version
        self.__db_version_info = db_version.DBVersionInfo(database_version['major'],
                                                   database_version['minor'])
        Context.__instance = self

    def set_env(self, env_vars):
        '''
        get the environment variables
        '''
        super(Context, self).set_env(env_vars)

        # get generic package specific environment variables
        self.logger_bin = os.environ.get(env_vars['cc_logger_bin'])
        self.logger_file = os.environ.get(env_vars['cc_logger_file'])
        self.logger_compilers = os.environ.get(env_vars['cc_logger_compiles'])
        self.ld_preload = os.environ.get(env_vars['ld_preload'])
        self.ld_lib_path = env_vars['env_ld_lib_path']

    def __get_version(self, version_file):
        '''
        get the package version fron the verison config file
        '''
        try:
            with open(version_file, 'r') as vfile:
                vfile_data = json.loads(vfile.read())

            package_version = vfile_data['version']
            db_version = vfile_data['db_version']

        except ValueError as verr:
            # db_version is required to know if the db schema is compatible
            LOG.error('Failed to get version info from the version file')
            LOG.error(verr)
            sys.exit(1)

        return package_version, db_version

    @property
    def default_checkers_config(self):
        return self.__checker_config

    @property
    def version(self):
        return self.__package_version

    @property
    def db_version_info(self):
        return self.__db_version_info

    @property
    def version_file(self):
        return os.path.join(self.__package_root, self.pckg_layout['version_file'])

    @property
    def env_var_cc_logger_bin(self):
        return self.env_vars['cc_logger_bin']

    @property
    def env_var_cc_logger_file(self):
        return self.env_vars['cc_logger_file']

    @property
    def env_var_cc_logger_compiles(self):
        return self.env_vars['cc_logger_compiles']

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
    def compiler_resource_dirs(self):
        compiler_resource_dirs = self.pckg_layout.get('compiler_resource_dirs')
        if not compiler_resource_dirs:
            return []
        else:
            inc_dirs = []
            for path in compiler_resource_dirs:
                if os.path.isabs(path):
                    inc_dirs.append(path)
                else:
                    inc_dirs.append(os.path.join(self.__package_root, path))
            return inc_dirs

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
            # set default analyzers assume they are in the PATH
            # will be checked later
            # key naming in the dict should be the same as in
            # the supported analyzers list
            analyzers['ClangSA'] = 'clang'
            analyzers['Clang-tidy'] = 'clang-tidy'
        else:
            for name, value in compiler_binaries.iteritems():
                if os.path.isabs(value):
                    # check if it is an absolute path
                    analyzers[name] = value
                else:
                    # check if it is a package relative path
                    relpath = os.path.dirname(value)
                    if relpath:
                        analyzers[name] =  os.path.join(self.__package_root, value)

        return analyzers

def get_context():

    LOG.debug('Loading package config')

    package_root = os.environ['CC_PACKAGE_ROOT']

    pckg_config_file = os.path.join(package_root, "config", "config.json")
    LOG.debug('Reading config: ' + pckg_config_file)
    with open(pckg_config_file, 'r') as cfg:
        cfg_dict = json.loads(cfg.read())

    LOG.debug(cfg_dict)

    LOG.debug('Loading layout config')

    layout_cfg_file = os.path.join(package_root, "config", "package_layout.json")
    LOG.debug(layout_cfg_file)
    with open(layout_cfg_file, 'r') as lcfg:
        lcfg_dict = json.loads(lcfg.read())

    # merge static and runtime layout
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
