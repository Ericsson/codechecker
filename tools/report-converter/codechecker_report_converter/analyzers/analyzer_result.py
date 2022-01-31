# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import json
import logging
import os

from abc import ABCMeta, abstractmethod
from collections import defaultdict
import hashlib
from typing import Dict, List, Optional

from codechecker_report_converter.report import Report, report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType
from codechecker_report_converter.report.parser.base import AnalyzerInfo


LOG = logging.getLogger('report-converter')


class AnalyzerResultBase(metaclass=ABCMeta):
    """ Base class to transform analyzer result. """

    # Short name of the analyzer.
    TOOL_NAME: str = ''

    # Full name of the analyzer.
    NAME: str = ''

    # Link to the official analyzer website.
    URL: str = ''

    def transform(
        self,
        analyzer_result_file_path: str,
        output_dir_path: str,
        export_type: str,
        file_name: str = "{source_file}_{analyzer}_{file_hash}",
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Converts the given analyzer result to the output directory in the given
        output type.
        """
        parser = report_file.get_parser(f".{export_type}")
        if not parser:
            LOG.error("The given output type '%s' is not supported!",
                      export_type)
            return False

        analyzer_result_file_path = os.path.abspath(analyzer_result_file_path)
        reports = self.get_reports(analyzer_result_file_path)
        if not reports:
            LOG.info("No '%s' results can be found in the given code analyzer "
                     "output.", self.TOOL_NAME)
            return False

        self._post_process_result(reports)

        for report in reports:
            report.analyzer_result_file_path = analyzer_result_file_path

            if not report.checker_name:
                report.checker_name = self.TOOL_NAME

        self._write(
            reports, output_dir_path, parser, export_type, file_name)

        if metadata:
            self._save_metadata(metadata, output_dir_path)
        else:
            LOG.warning("Use '--meta' option to provide extra information "
                        "to the CodeChecker server such as analyzer version "
                        "and analysis command when storing the results to it. "
                        "For more information see the --help.")

        return True

    @abstractmethod
    def get_reports(self, analyzer_result_file_path: str) -> List[Report]:
        """ Get reports from the given analyzer result. """
        raise NotImplementedError("Subclasses should implement this!")

    def _save_metadata(self, metadata, output_dir):
        """ Save metadata.json file to the output directory which will be used
        by CodeChecker.
        """
        meta_info = {
            "version": 2,
            "num_of_report_dir": 1,
            "tools": []
        }

        tool = {"name": self.TOOL_NAME}

        if "analyzer_version" in metadata:
            tool["version"] = metadata["analyzer_version"]

        if "analyzer_command" in metadata:
            tool["command"] = metadata["analyzer_command"]

        meta_info["tools"].append(tool)

        metadata_file = os.path.join(output_dir, 'metadata.json')
        with open(metadata_file, 'w',
                  encoding="utf-8", errors="ignore") as metafile:
            json.dump(meta_info, metafile)

    def _post_process_result(self, reports: List[Report]):
        """ Post process the parsed result.

        By default it will add report hashes and metada information.
        """
        for report in reports:
            self._add_report_hash(report)
            self._add_metadata(report)

    def _add_report_hash(self, report: Report):
        """ Generate report hash for the given plist data. """
        report.report_hash = get_report_hash(report, HashType.CONTEXT_FREE)

    def _add_metadata(self, report: Report):
        """ Add metada information to the given plist data. """
        report.analyzer_name = self.TOOL_NAME

    def _write(
        self,
        reports: List[Report],
        output_dir_path: str,
        parser,
        export_type: str,
        file_name: str
    ):
        """ Creates plist files from the parse result to the given output.

        It will generate a context free hash for each diagnostics.
        """
        output_dir = os.path.abspath(output_dir_path)

        file_to_report: Dict[str, List[Report]] = defaultdict(list)
        for report in reports:
            file_path = os.path.normpath(report.file.original_path)
            file_to_report[file_path].append(report)

        analyzer_info = AnalyzerInfo(name=self.TOOL_NAME)
        for file_path, file_reports in file_to_report.items():
            source_file = os.path.basename(file_path)
            file_hash = hashlib.md5(file_path.encode(errors='ignore')) \
                .hexdigest()

            out_file_name = file_name \
                .replace("{source_file}", source_file) \
                .replace("{analyzer}", self.TOOL_NAME) \
                .replace("{file_hash}", file_hash)
            out_file_name = f"{out_file_name}.{export_type}"
            out_file_path = os.path.join(output_dir, out_file_name)

            LOG.info("Create/modify plist file: '%s'.", out_file_path)
            LOG.debug(file_reports)

            data = parser.convert(file_reports, analyzer_info)
            parser.write(data, out_file_path)
