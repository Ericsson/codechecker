# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import os

from typing import Dict, Iterator, List, Optional, Tuple

from codechecker_report_converter.report import File, Report
from codechecker_report_converter.report.checker_labels import CheckerLabels
from codechecker_report_converter.report.hash import HashType
from codechecker_report_converter.report.parser import plist
from codechecker_report_converter.report.parser.base import AnalyzerInfo


LOG = logging.getLogger('report-converter')


SUPPORTED_ANALYZER_EXTENSIONS = [plist.EXTENSION]


__SUPPORTED_ANALYZER_EXTENSIONS = tuple([
    f".{extension}" for extension in SUPPORTED_ANALYZER_EXTENSIONS])


def is_supported(analyzer_result_file_path: str) -> bool:
    """ True if the given report file can be parsed. """
    return analyzer_result_file_path.endswith(__SUPPORTED_ANALYZER_EXTENSIONS)


def get_parser(
    analyzer_result_file_path: str,
    checker_labels: Optional[CheckerLabels] = None,
    file_cache: Optional[Dict[str, File]] = None
):
    """ Returns a parser object for the given analyzer result file. """
    if analyzer_result_file_path.endswith(f".{plist.EXTENSION}"):
        return plist.Parser(checker_labels, file_cache)


def get_reports(
    analyzer_result_file_path: str,
    checker_labels: Optional[CheckerLabels] = None,
    file_cache: Optional[Dict[str, File]] = None,
    source_dir_path: Optional[str] = None
) -> List[Report]:
    """ Get reports from the given report file. """
    parser = get_parser(analyzer_result_file_path, checker_labels, file_cache)

    if parser:
        return parser.get_reports(analyzer_result_file_path, source_dir_path)

    return []


def create(
    output_file_path: str,
    reports: List[Report],
    checker_labels: Optional[CheckerLabels] = None,
    analyzer_info: Optional[AnalyzerInfo] = None
):
    """ Creates an analyzer output file from the given reports. """
    parser = get_parser(output_file_path, checker_labels)

    if parser:
        data = parser.convert(reports, analyzer_info)
        parser.write(data, output_file_path)


def replace_report_hash(
    analyzer_result_file_path: str,
    hash_type=HashType.CONTEXT_FREE
):
    """ Override hash in the given file by using the given version hash. """
    parser = get_parser(analyzer_result_file_path)

    if parser:
        parser.replace_report_hash(
            analyzer_result_file_path, hash_type)


def analyzer_result_files(
    input_paths: List[str]
) -> Iterator[Tuple[str, List[str]]]:
    """
    Iterate over the input paths and returns an iterator of the supported
    analyzer result file paths and metadata information if available.
    """
    for input_path in input_paths:
        input_path = os.path.abspath(input_path)
        LOG.debug("Parsing input argument: '%s'", input_path)

        if os.path.isfile(input_path):
            input_dir_path = os.path.dirname(input_path)
            if is_supported(input_path):
                yield input_dir_path, [input_path]
        elif os.path.isdir(input_path):
            input_dir_path = input_path
            for root_dir, _, file_names in os.walk(input_path):
                analyzer_result_file_paths: List[str] = []
                for file_name in file_names:
                    input_file_path = os.path.join(root_dir, file_name)
                    if is_supported(input_file_path):
                        analyzer_result_file_paths.append(input_file_path)

                yield root_dir, analyzer_result_file_paths
