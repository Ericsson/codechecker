# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Clang Static Analyzer related functions.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import re
import subprocess

from codechecker_common.logger import get_logger
from codechecker_analyzer import host_check

LOG = get_logger('analyzer.clangsa')


def invoke_binary_checked(binary_path, args=None, environ=None):
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
    try:
        output = subprocess.check_output(invocation, env=environ)
    except subprocess.CalledProcessError as e:
        LOG.debug(
            'Command invocation failed because of non-zero exit code!'
            'Details: {}'.format(str(e)))
        return False
    return output


class ClangVersionInfo(object):
    """
    ClangVersionInfo holds the relevant version information of the used Clang
    tool.
    """

    def __init__(self,
                 major_version=None,
                 minor_version=None,
                 patch_version=None,
                 installed_dir=None):

        self.major_version = int(major_version)
        self.minor_version = int(minor_version)
        self.patch_version = int(patch_version)
        self.installed_dir = str(installed_dir)


class ClangVersionInfoParser(object):
    """
    ClangVersionInfoParser is responsible for creating ClangVersionInfo
    instances from the version output of Clang.
    """

    def __init__(self):
        self.clang_version_pattern = (
            r'clang version (?P<major_version>[0-9]+)'
            r'\.(?P<minor_version>[0-9]+)\.(?P<patch_version>[0-9]+)')

        self.clang_installed_dir_pattern =\
            r'InstalledDir: (?P<installed_dir>[^\s]*)'

    def parse(self, version_string):
        """
        Try to parse the version string using the predefined patterns.
        """

        version_match = re.search(self.clang_version_pattern, version_string)
        installed_dir_match = re.search(
            self.clang_installed_dir_pattern, version_string)

        if not version_match or not installed_dir_match:
            return False

        return ClangVersionInfo(
            version_match.group('major_version'),
            version_match.group('minor_version'),
            version_match.group('patch_version'),
            installed_dir_match.group('installed_dir'))


class CTUAutodetection(object):
    """
    CTUAutodetection is responsible for providing the availability information
    of CTU feature, the the relevant mapping tool path and the mapping file
    name.
    """

    def __init__(self, analyzer_binary, environ):
        self.__analyzer_binary = analyzer_binary
        self.__analyzer_version_info = None
        self.environ = environ
        self.parser = ClangVersionInfoParser()

        self.old_mapping_tool_name = 'clang-func-mapping'
        self.new_mapping_tool_name = 'clang-extdef-mapping'

        self.old_mapping_file_name = 'externalFnMap.txt'
        self.new_mapping_file_name = 'externalDefMap.txt'

    @property
    def analyzer_version_info(self):
        """
        Returns the relevant parameters of the analyzer by parsing the
        output of the analyzer binary when called with version flag.
        """

        if self.__analyzer_binary is None:
            LOG.debug(
                'Trying to detect CTU capability, but analyzer binary is not '
                'set!')
            return False

        analyzer_version = invoke_binary_checked(
            self.__analyzer_binary, ['--version'], self.environ)

        if analyzer_version is False:
            LOG.debug('Failed to invoke command to get Clang version!')
            return False

        version_info = self.parser.parse(analyzer_version)

        if not version_info:
            LOG.debug('Failed to parse Clang version information!')
            return False

        self.__analyzer_version_info = version_info
        return self.__analyzer_version_info

    @property
    def major_version(self):
        """
        Returns the major version of the analyzer, which is used for
        CTU analysis.
        """

        if not self.analyzer_version_info:
            return False

        return self.analyzer_version_info.major_version

    @property
    def installed_dir(self):
        """
        Returns the installed directory of the analyzer, which is used for
        CTU analysis.
        """

        if not self.analyzer_version_info:
            return False

        return self.analyzer_version_info.installed_dir

    @property
    def mapping_tool_path(self):
        """
        Returns the path of the mapping tool, which is assumed to be located
        inside the installed directory of the analyzer. Certain binary
        distributions can postfix the the tool name with the major version
        number, the the number and the tool name being separated by a dash. By
        default the shorter name is looked up, then if it is not found the
        postfixed.
        """

        if not self.analyzer_version_info:
            return False

        major_version = self.analyzer_version_info.major_version
        installed_dir = self.analyzer_version_info.installed_dir

        tool_name = self.new_mapping_tool_name if major_version > 7 else\
            self.old_mapping_tool_name

        tool_path = os.path.join(installed_dir, tool_name)

        if os.path.isfile(tool_path):
            return tool_path

        LOG.debug(
            "Mapping tool '{}' suggested by autodetection is not found in "
            "directory reported by Clang '{}'. Trying with version-postfixed "
            "filename...".format(tool_path, installed_dir))

        postfixed_tool_path = ''.join([tool_path, '-', str(major_version)])

        if os.path.isfile(postfixed_tool_path):
            return postfixed_tool_path

        LOG.debug(
            "Postfixed mapping tool '{}' suggested by autodetection is not "
            "found in directory reported by Clang '{}'."
            .format(postfixed_tool_path, installed_dir))

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
            self.__analyzer_binary, "display-ctu-progress", self.environ)
        if not ok:
            return None
        return ctu_display_progress_args

    @property
    def mapping_file_name(self):
        """
        Returns the installed directory of the analyzer, which is used for
        CTU analysis.
        """

        if not self.analyzer_version_info:
            return False

        major_version = self.analyzer_version_info.major_version

        return self.new_mapping_file_name if major_version > 7 else\
            self.old_mapping_file_name

    @property
    def is_ctu_capable(self):
        """
        Detects if the current clang is CTU compatible. Tries to autodetect
        the correct one based on clang version.
        """

        tool_path = self.mapping_tool_path

        if not tool_path:
            return False

        return invoke_binary_checked(tool_path, ['-version'], self.environ) \
            is not False
