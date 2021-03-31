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

import subprocess

from codechecker_common.logger import get_logger
from codechecker_analyzer.analyzers.clangsa import clang_options, version

from typing import Dict, Optional, List

LOG = get_logger('analyzer.clangsa')

CTU_ON_DEMAND_OPTION_NAME = 'ctu-invocation-list'
CTU_DISPLAY_PROGRESS_OPTION_NAME = 'display-ctu-progress'


class CTUAutodetection:
    """
    CTUAutodetection is responsible for providing the availability information
    of CTU feature, the the relevant mapping tool path and the mapping file
    name.
    """

    @staticmethod
    def _invoke_binary_checked(
            binary_path: str, args: Optional[List[str]] = None,
            environ: Optional[Dict[str, str]] = None) -> str:
        """
        Invokes a binary with the specified args, and environment.

        Parameters
        ----------
        binary_path : str
            The path to the executable to invoke
        args : list[str]
            The arguments of the invocation

        Returns
        -------
        str
            The content of the standard output of the called process.

        Raises
        ------
        CalledProcessError
            Fom underlying subprocess module.
        OSError
            Fom underlying subprocess module.
        """

        args = args or []
        invocation = [binary_path]
        invocation.extend(args)
        try:
            output = subprocess.check_output(
                invocation,
                env=environ,
                encoding="utf-8",
                errors="ignore")
        except (subprocess.CalledProcessError, OSError) as ex:
            LOG.debug(
                'Command invocation "{}" failed because of non-zero exit code!'
                'Details: {}'.format(invocation, str(ex)))
            raise ex
        return output

    def __init__(self, analyzer_binary: str,
                 environment: Optional[Dict[str, str]]):
        """
        Parameters
        ----------
        analyzer_binary : str
            Full path name of the executable.
        environment : dict
            Environment variable definitions.

        Raises
        ------
        CalledProcessError
            Fom underlying subprocess module.
        OSError
            Fom underlying subprocess module.
        """

        assert (analyzer_binary is not None), \
            'Trying to detect CTU capability, but analyzer binary is not set!'

        self.__analyzer_binary = analyzer_binary
        self.__environment = environment
        analyzer_version = CTUAutodetection._invoke_binary_checked(
            self.__analyzer_binary, ['--version'], self.__environment)

        if analyzer_version is False:
            LOG.debug('Failed to invoke command to get Clang version!')
            return None

        version_parser = version.ClangVersionInfoParser()
        self.__analyzer_version_info = version_parser.parse(analyzer_version)

        if not self.__analyzer_version_info:
            LOG.debug('Failed to parse Clang version information!')
            self.__tool_path = None
            self.__mapping_file_name = None
        else:
            self.__tool_path, self.__mapping_file_name = \
                clang_options.ctu_mapping(self.__analyzer_version_info)

        self.__analyzer_options = CTUAutodetection._invoke_binary_checked(
            self.__analyzer_binary, ['-cc1', '-analyzer-config-help'],
            self.__environment)

        self.__display_ctu_progress_options = \
            self.__get_display_ctu_progress_options()
        self.__on_demand_ctu_available = self.__get_on_demand_ctu_available()
        self.__ctu_capable = self.__get_ctu_capable()

    @property
    def installed_dir(self) -> str:
        """
        Queries the installed directory of the analyzer, which is used for
        CTU analysis.

        Returns
        -------
        str
            Directory name or None if it could not be detected.
        """

        return self.__analyzer_version_info.installed_dir

    @property
    def mapping_tool_path(self) -> Optional[str]:
        """
        Queries the path to the mapping tool.

        Returns
        -------
        bool
            Full path of the name of executable or None if it could not be
            detected.
        """

        return self.__tool_path

    @property
    def display_progress_options(self) -> Optional[List[str]]:
        """
        Queries analyzer args to display ctu progress.

        Returns
        -------
        list[str]
            Returns a list of ctu display progress arguments depend on the
            current clang analyzer version.
            Otherwise None if the analyzer can not display ctu progress.
        """

        return self.__display_ctu_progress_options

    def __get_display_ctu_progress_options(self) -> Optional[List[str]]:
        """
        Detects availability of 'display ctu progress' feature of clang.

        Returns
        -------
        list[str]
            Returns a list of ctu display progress arguments depend on the
            current clang analyzer version.
            None if the analyzer can not display ctu progress.
        """

        if CTU_DISPLAY_PROGRESS_OPTION_NAME in self.__analyzer_options:
            return ['-Xclang', '-analyzer-config', '-Xclang',
                    'display-ctu-progress=true']
        else:
            return None

    @property
    def mapping_file_name(self) -> Optional[str]:
        """
        Queries the 'clang external def mapping file', which is used for
        CTU analysis.

        Returns
        -------
        str
            Full path of the name of mapping file or None if it could not be
            detected.
        """

        return self.__mapping_file_name

    @property
    def is_ctu_capable(self) -> bool:
        """
        Queries if the current clang is CTU compatible.

        Returns
        -------
        bool
            True if analyzer capable of CTU analysis, otherwise False.
        """

        return self.__ctu_capable

    def __get_ctu_capable(self) -> bool:
        """
        Detects if the current clang is CTU compatible. Tries to autodetect
        the correct one based on clang version.

        Returns
        -------
        bool
            True if analyzer capable of CTU analysis, otherwise False.
        """

        if not self.__tool_path:
            return False

        return CTUAutodetection._invoke_binary_checked(
            self.__tool_path, ['-version'], self.__environment) is not False

    @property
    def is_on_demand_ctu_available(self) -> bool:
        """
        Query CTU analysis capability of underlying analyzer.

        Returns
        -------
        bool
            True if analyzer capable of CTU analysis, otherwise False.
        """

        return self.__on_demand_ctu_available

    def __get_on_demand_ctu_available(self) -> bool:
        """
        Detects if the current Clang supports on-demand parsing of ASTs for
        CTU analysis.

        Returns
        -------
        bool
            True if analyzer capable of CTU analysis, otherwise False.
        """

        if not self.__analyzer_options:
            return False

        return CTU_ON_DEMAND_OPTION_NAME in self.__analyzer_options
