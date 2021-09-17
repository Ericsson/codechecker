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
import os
import re
import sys

from codechecker_report_converter.util import load_json_or_empty

from codechecker_common import logger
from codechecker_common.checker_labels import CheckerLabels
from codechecker_common.singleton import Singleton

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


# -----------------------------------------------------------------------------
class Context(metaclass=Singleton):
    """ Generic package specific context. """

    def __init__(self):
        """ Initialize web context. """
        self._lib_dir_path = os.environ.get('CC_LIB_DIR', '')
        self._data_files_dir_path = os.environ.get('CC_DATA_FILES_DIR', '')

        lcfg_dict = self.__get_package_layout()
        self.pckg_layout = lcfg_dict['runtime']

        # Use this environment variable for testing purposes only. This
        # variable helps to configure which labels to use in this context.
        labels_dir = os.path.join(self._data_files_dir_path,
                                  'config', 'labels')
        if 'CC_TEST_LABELS_DIR' in os.environ:
            labels_dir = os.environ['CC_TEST_LABELS_DIR']

        self._checker_labels = CheckerLabels(labels_dir)
        self.__system_comment_map = \
            load_json_or_empty(self.system_comment_map_file, {})
        self.__git_commit_urls = self.__get_git_commit_urls()
        self.__package_version = None
        self.__package_build_date = None
        self.__package_git_hash = None

        # This should be initialized in command line scripts based on the
        # given CLI options.
        self.codechecker_workspace = None

        self.__set_version()

    def __get_git_commit_urls(self):
        """ Get commit urls from the configuration file. """
        git_commit_urls = load_json_or_empty(self.git_commit_urls_file, [])

        for git_commit_url in git_commit_urls:
            git_commit_url["regex"] = re.compile(git_commit_url["regex"])

        return git_commit_urls

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
                            'web_version.json')

    @property
    def system_comment_map(self):
        return self.__system_comment_map

    @property
    def system_comment_map_file(self):
        return os.path.join(self._data_files_dir_path, 'config',
                            'system_comment_kinds.json')

    @property
    def git_commit_urls_file(self):
        return os.path.join(
            self._data_files_dir_path, 'config', 'git_commit_urls.json')

    @property
    def git_commit_urls(self):
        return self.__git_commit_urls

    @property
    def path_plist_to_html_dist(self):
        return os.path.join(self._lib_dir_path, 'codechecker_report_converter',
                            'report', 'output', 'html', 'static')

    @property
    def path_env_extra(self):
        extra_paths = self.pckg_layout.get('path_env_extra', [])
        paths = []
        for path in extra_paths:
            paths.append(os.path.join(self._data_files_dir_path, path))
        return paths

    @property
    def ld_lib_path_extra(self):
        extra_lib = self.pckg_layout.get('ld_lib_path_extra', [])
        ld_paths = []
        for path in extra_lib:
            ld_paths.append(os.path.join(self._data_files_dir_path, path))
        return ld_paths

    @property
    def data_files_dir_path(self):
        return self._data_files_dir_path

    @property
    def doc_root(self):
        return os.path.join(self._data_files_dir_path, 'www', 'docs')

    @property
    def www_root(self):
        return os.path.join(self._data_files_dir_path, 'www')

    @property
    def run_migration_root(self):
        return os.path.join(self._lib_dir_path, 'codechecker_server',
                            'migrations', 'report')

    @property
    def config_migration_root(self):
        return os.path.join(self._lib_dir_path, 'codechecker_server',
                            'migrations', 'config')

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
