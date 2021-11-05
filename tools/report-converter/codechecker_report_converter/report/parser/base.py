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

import logging

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Optional

from codechecker_report_converter.report import File, Report
from codechecker_report_converter.report.checker_labels import CheckerLabels
from codechecker_report_converter.report.hash import HashType


LOG = logging.getLogger('report-converter')


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
