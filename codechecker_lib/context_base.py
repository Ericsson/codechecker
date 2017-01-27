# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import abc
import json
import os
from codechecker_lib.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger("CONTEXT BASE")


# -----------------------------------------------------------------------------
class ContextBase(object):
    __metaclass__ = abc.ABCMeta

    _package_root = None
    _verbose_level = None
    _alchemy_log_level = None
    _env_path = None
    _env_vars = None
    _extra_include_paths = []
    _compiler_sysroot = None
    _extra_system_include_paths = []
    _codechecker_enable_checkers = set()
    _codechecker_disable_checkers = set()
    _codechecker_workspace = None
    _db_username = None
    _module_id = ''
    _run_id = None
    _severity_map = dict()

    def load_data(self, env_vars, pckg_layout, variables):
        self.pckg_layout = pckg_layout
        self.variables = variables
        self.env_vars = env_vars

        self.set_env(env_vars)
        self._db_username = self.variables['default_db_username']

    @abc.abstractmethod
    def set_env(self, env_vars):
        self._package_root = os.environ.get(env_vars['env_package_root'])
        self._verbose_level = os.environ.get(env_vars['env_verbose_name'])
        self._alchemy_log_level = \
            os.environ.get(env_vars['env_alchemy_verbose_name'])
        self._env_path = os.environ.get(env_vars['env_path'])
        env_enabled_checkers = os.environ.get(
            env_vars['codechecker_enable_check'])
        if env_enabled_checkers:
            self._codechecker_enable_checkers = \
                set(env_enabled_checkers.split(':'))

        env_disabled_checkers = os.environ.get(
            env_vars['codechecker_disable_check'])

        if env_disabled_checkers:
            self._codechecker_disable_checkers = \
                set(env_disabled_checkers.split(':'))

        codechecker_workspace = os.environ.get('codechecker_workspace')
        if codechecker_workspace:
            self._codechecker_workspace = codechecker_workspace

        try:
            with open(self.checkers_severity_map_file) as severity_file:
                self._severity_map = json.load(severity_file)
        except (IOError, ValueError):
            LOG.warning(self.checkers_severity_map_file + " doesn't exist or "
                        "not JSON format. Severity levels will not be "
                        "available!")

    @property
    def package_root(self):
        return self._package_root

    @property
    def verbose_level(self):
        return self._verbose_level

    @property
    def checker_plugin(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['plugin'])

    @property
    def clang_include(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['compiler_include'])

    @property
    def extra_includes(self):
        return self._extra_include_paths

    @extra_includes.setter
    def add_extra_includes(self, path):
        self._extra_include_paths.append(path)

    @property
    def extra_system_includes(self):
        return self._extra_system_include_paths

    @extra_includes.setter
    def add_extra_system_includes(self, path):
        self._extra_system_include_paths.append(path)

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
    def migration_root(self):
        return os.path.join(self._package_root,
                            self.pckg_layout['codechecker_db_migrate'])

    @property
    def db_username(self):
        return self._db_username

    @db_username.setter
    def db_username(self, value):
        self._db_username = value

    @property
    def pgsql_data_dir_name(self):
        return self.variables['pgsql_data_dir_name']

    @property
    def env_enabled_checkers(self):
        return self._codechecker_enable_checkers

    @env_enabled_checkers.setter
    def env_enabled_checkers(self, value):
        self._codechecker_enable_checkers = \
            self._codechecker_enable_checkers.union(value)

    @property
    def env_disabled_checkers(self):
        return self._codechecker_disable_checkers

    @env_disabled_checkers.setter
    def env_disabled_checkers(self, value):
        self._codechecker_disable_checkers = \
            self._codechecker_disable_checkers.union(value)

    @property
    def codechecker_workspace(self):
        return self._codechecker_workspace

    @codechecker_workspace.setter
    def codechecker_workspace(self, value):
        self._codechecker_workspace = value

    @property
    def database_path(self):
        return os.path.join(self.codechecker_workspace,
                            self.pgsql_data_dir_name)

    @property
    def compiler_sysroot(self):
        return self._compiler_sysroot

    @compiler_sysroot.setter
    def compiler_sysroot(self, value):
        self._compiler_sysroot = value

    @property
    def module_id(self):
        return self._module_id

    @module_id.setter
    def module_id(self, value):
        self._module_id = value

    @property
    def run_id(self):
        return self._run_id

    @run_id.setter
    def run_id(self, value):
        self._run_id = value

    @property
    def severity_map(self):
        return self._severity_map
