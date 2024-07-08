# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Base parser class to parse analyzer result files.
"""

import json
import logging
import os

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from codechecker_report_converter import __title__, __version__
from codechecker_report_converter.report import File, Report
from codechecker_report_converter.report.checker_labels import CheckerLabels
from codechecker_report_converter.report.hash import HashType


LOG = logging.getLogger('report-converter')


def load_json(path: str):
    """
    Load the contents of the given file as a JSON and return it's value,
    or default if the file can't be loaded.
    """

    ret = {}
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            ret = json.load(handle)
    except OSError as ex:
        LOG.warning("Failed to open json file: %s", path)
        LOG.warning(ex)
    except ValueError as ex:
        LOG.warning("%s is not a valid json file.", path)
        LOG.warning(ex)
    except TypeError as ex:
        LOG.warning('Failed to process json file: %s', path)
        LOG.warning(ex)

    return ret


def get_tool_info() -> Tuple[str, str]:
    """ Get tool info.

    If this was called through CodeChecker, this function will return
    CodeChecker information, otherwise this tool (report-converter)
    information.
    """
    data_files_dir_path = os.environ.get('CC_DATA_FILES_DIR')
    if data_files_dir_path:
        analyzer_version_file_path = os.path.join(
            data_files_dir_path, 'config', 'analyzer_version.json')
        if os.path.exists(analyzer_version_file_path):
            data = load_json(analyzer_version_file_path)
            version = data.get('version')
            if version:
                return 'CodeChecker', f"{version['major']}." \
                    f"{version['minor']}.{version['revision']}"

    return __title__, __version__


class AnalyzerInfo:
    """ Hold information about the analyzer. """
    def __init__(self, name: str):
        self.name = name


class BaseParser(metaclass=ABCMeta):
    """ Base class to manage analyzer result file. """
    def __init__(
        self,
        checker_labels: Optional[CheckerLabels] = None,
        file_cache: Optional[Dict[str, File]] = None
    ):
        self._checker_labels = checker_labels
        self._file_cache = file_cache if file_cache is not None else {}

    def get_severity(self, checker_name: str) -> Optional[str]:
        """ Get severity levels for the given checker name. """
        if self._checker_labels:
            return self._checker_labels.severity(checker_name)
        return None

    @abstractmethod
    def get_reports(
        self,
        analyzer_result_file_path: str
    ) -> List[Report]:
        """ Get reports from the given analyzer result file. """
        raise NotImplementedError("Subclasses should implement this!")

    @abstractmethod
    def convert(
        self,
        reports: List[Report],
        analyzer_info: Optional[AnalyzerInfo] = None
    ):
        """ Converts the given reports. """
        raise NotImplementedError("Subclasses should implement this!")

    @abstractmethod
    def write(self, data: Any, output_file_path: str):
        """ Creates an analyzer output file from the given data. """
        raise NotImplementedError("Subclasses should implement this!")

    @abstractmethod
    def replace_report_hash(
        self,
        analyzer_result_file_path: str,
        hash_type=HashType.CONTEXT_FREE
    ):
        """
        Override hash in the given file by using the given version hash.
        """
        raise NotImplementedError("Subclasses should implement this!")
