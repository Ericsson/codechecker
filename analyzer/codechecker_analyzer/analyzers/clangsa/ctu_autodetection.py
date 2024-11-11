# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Clang Static Analyzer related functions.
"""

import os
import subprocess

from codechecker_common.logger import get_logger
from codechecker_analyzer import analyzer_context
from codechecker_analyzer import host_check
from codechecker_analyzer.analyzers.clangsa import version

LOG = get_logger('analyzer.clangsa')

CTU_ON_DEMAND_OPTION_NAME = 'ctu-invocation-list'


def ctu_mapping(clang_version_info):
    """Clang version dependent ctu mapping tool path and mapping file name.

    The path of the mapping tool, which is assumed to be located
    inside the installed directory of the analyzer. Certain binary
    distributions can postfix the tool name with the major version
    number, the number and the tool name being separated by a dash. By
    default the shorter name is looked up, then if it is not found the
    postfixed.
    """
    if not clang_version_info:
        LOG.debug("No clang version information."
                  "Can not detect ctu mapping tool.")
        return None, None

    old_mapping_tool_name = 'clang-func-mapping'
    old_mapping_file_name = 'externalFnMap.txt'

    new_mapping_tool_name = 'clang-extdef-mapping'
    new_mapping_file_name = 'externalDefMap.txt'

    major_version = clang_version_info.major_version

    if major_version > 7:
        tool_name = new_mapping_tool_name
        mapping_file = new_mapping_file_name
    else:
        tool_name = old_mapping_tool_name
        mapping_file = old_mapping_file_name

    installed_dir = clang_version_info.installed_dir

    tool_path = os.path.join(installed_dir, tool_name)

    if os.path.isfile(tool_path):
        return tool_path, mapping_file

    LOG.debug(
        "Mapping tool '%s' suggested by autodetection is not found in "
        "directory reported by Clang '%s'. Trying with version-postfixed "
        "filename...", tool_path, installed_dir)

    postfixed_tool_path = ''.join([tool_path, '-', str(major_version)])

    if os.path.isfile(postfixed_tool_path):
        return postfixed_tool_path, mapping_file

    LOG.debug(
        "Postfixed mapping tool '%s' suggested by autodetection is not "
        "found in directory reported by Clang '%s'.",
        postfixed_tool_path, installed_dir)
    return None, None


def invoke_binary_checked(binary_path, args=None):
    """
    Invoke the binary with the specified args, and return the output if the
    command finished running with zero exit code. Return False otherwise.
    Possible usage can be used to check the existence binaries.

    :param binary_path: The path to the executable to invoke
    :param args: The arguments of the invocation
    :type binary_path: str
    :type args: list
    :rtype str
    """

    args = args or []
    invocation = [binary_path]
    invocation.extend(args)
    environ = analyzer_context.get_context().get_env_for_bin(binary_path)
    try:
        output = subprocess.check_output(
            invocation,
            env=environ,
            encoding="utf-8",
            errors="ignore")
    except (subprocess.CalledProcessError, OSError) as e:
        LOG.debug('Command invocation failed because of non-zero exit code!'
                  'Details: %s', str(e))
        return False
    return output


class CTUAutodetection:
    """
    CTUAutodetection is responsible for providing the availability information
    of CTU feature, the the relevant mapping tool path and the mapping file
    name.
    """

    def __init__(self, analyzer_binary, environ):
        self.__analyzer_binary = analyzer_binary
        self.environ = environ
        self.__analyzer_version_info = None

        if self.__analyzer_binary is None:
            LOG.debug(
                'Trying to detect CTU capability, but analyzer binary is not '
                'set!')
            return

        analyzer_version = invoke_binary_checked(
            self.__analyzer_binary, ['--version'])

        if analyzer_version is False:
            LOG.debug('Failed to invoke command to get Clang version!')
            return

        version_parser = version.ClangVersionInfoParser(self.__analyzer_binary)
        version_info = version_parser.parse(analyzer_version)

        if not version_info:
            LOG.debug('Failed to parse Clang version information!')
            return

        self.__analyzer_version_info = version_info

    @property
    def analyzer_version_info(self):
        """
        Returns the relevant parameters of the analyzer by parsing the
        output of the analyzer binary when called with version flag.
        """
        if not self.__analyzer_version_info:
            return False

        return self.__analyzer_version_info

    @property
    def major_version(self):
        """
        Returns the major version of the analyzer, which is used for
        CTU analysis.
        """
        return self.analyzer_version_info.major_version

    @property
    def installed_dir(self):
        """
        Returns the installed directory of the analyzer, which is used for
        CTU analysis.
        """
        return self.analyzer_version_info.installed_dir

    @property
    def mapping_tool_path(self):
        """Return the path to the mapping tool."""
        tool_path, _ = ctu_mapping(self.analyzer_version_info)

        if tool_path:
            return tool_path
        return False

    @property
    def display_progress(self):
        """
        Return analyzer args if it is capable to display ctu progress.

        Returns None if the analyzer can not display ctu progress.
        The ctu display progress arguments depend on
        the clang analyzer version.
        """

        if not self.analyzer_version_info:
            return None
        ctu_display_progress_args = ['-Xclang',
                                     '-analyzer-config',
                                     '-Xclang',
                                     'display-ctu-progress=true']

        ok = host_check.has_analyzer_config_option(
            self.__analyzer_binary, "display-ctu-progress")
        if not ok:
            return None
        return ctu_display_progress_args

    @property
    def mapping_file_name(self):
        """
        Returns the installed directory of the analyzer, which is used for
        CTU analysis.
        """

        _, mapping_file_name = ctu_mapping(self.analyzer_version_info)

        if mapping_file_name:
            return mapping_file_name
        return False

    @property
    def is_ctu_capable(self):
        """
        Detects if the current clang is CTU compatible. Tries to autodetect
        the correct one based on clang version.
        """

        tool_path = self.mapping_tool_path

        if not tool_path:
            return False

        return invoke_binary_checked(tool_path, ['-version']) \
            is not False

    @property
    def is_on_demand_ctu_available(self):
        """
        Detects if the current Clang supports on-demand parsing of ASTs for
        CTU analysis.
        """

        analyzer_options = invoke_binary_checked(
            self.__analyzer_binary, ['-cc1', '-analyzer-config-help'])

        if analyzer_options is False:
            return False

        return CTU_ON_DEMAND_OPTION_NAME in analyzer_options
