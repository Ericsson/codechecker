# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Result handler for Gcc.
"""
from typing import Optional
from pathlib import Path
import shutil
import os

from codechecker_report_converter.report.parser.base import AnalyzerInfo
from codechecker_report_converter.analyzers.gcc.analyzer_result import \
    AnalyzerResult
from codechecker_report_converter.report import report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType

from codechecker_common.logger import get_logger
from codechecker_common.skiplist_handler import SkipListHandlers

from ..result_handler_base import ResultHandler

LOG = get_logger('analyzer.gcc')


def actual_name_to_codechecker_name(actual_name: str):
    assert actual_name.startswith('-Wanalyzer')
    return actual_name.replace("-Wanalyzer", "gcc")


def codechecker_name_to_actual_name(codechecker_name: str):
    assert codechecker_name.startswith('gcc')
    return codechecker_name.replace("gcc", "-Wanalyzer")


def codechecker_name_to_actual_name_disabled(codechecker_name: str):
    assert codechecker_name.startswith('gcc')
    return codechecker_name.replace("gcc", "-Wno-analyzer")


class GccResultHandler(ResultHandler):
    """
    Create analyzer result file for Gcc output.
    """

    def __init__(self, *args, **kwargs):
        self.analyzer_info = AnalyzerInfo(name=AnalyzerResult.TOOL_NAME)
        self.gcc_analyzer_result = AnalyzerResult()

        super(GccResultHandler, self).__init__(*args, **kwargs)

    def postprocess_result(self, skip_handlers: Optional[SkipListHandlers]):
        """
        Generate analyzer result output file which can be parsed and stored
        into the database.
        """
        LOG.debug_analyzer(self.analyzer_stdout)
        gcc_stderr = self.analyzer_stderr
        assert gcc_stderr, "Even in the event of no reported diagnostics, " \
                           "stderr mustn't be empty!"

        # report-converter needs a file to parse, let's dump the content of
        # stderr to one.
        gcc_out_folder = Path(self.workspace, "gcc")
        gcc_out_folder.mkdir(exist_ok=True)
        gcc_dest_file_name = \
            str(Path(gcc_out_folder,
                     os.path.basename(self.analyzed_source_file) +
                     self.buildaction_hash + ".sarif"))

        with open(gcc_dest_file_name, 'w') as f:
            f.write(gcc_stderr)
        assert os.path.exists(gcc_dest_file_name)

        reports = report_file.get_reports(
            gcc_dest_file_name, self.checker_labels,
            source_dir_path=self.source_dir_path)

        # FIXME: We absolutely want to support gcc compiler warnings
        # eventually (which don't start with '-Wanalyzer'), but we should
        # probably list them in the label files as well, etc.
        reports = \
            [r for r in reports if not r.skip(skip_handlers) and
             r.checker_name.startswith("-Wanalyzer")]

        # If we were to leave sarif files in the repoort directory, we would
        # unintentionally parse them, so we rename them.
        try:
            shutil.move(gcc_dest_file_name, gcc_dest_file_name + '.bak')
        except(OSError) as e:
            LOG.error(e)

        for report in reports:
            report.checker_name = \
                actual_name_to_codechecker_name(report.checker_name)

        hash_type = HashType.PATH_SENSITIVE
        if self.report_hash_type == 'context-free-v2':
            hash_type = HashType.CONTEXT_FREE
        elif self.report_hash_type == 'diagnostic-message':
            hash_type = HashType.DIAGNOSTIC_MESSAGE

        for report in reports:
            report.report_hash = get_report_hash(report, hash_type)

        report_file.create(
            self.analyzer_result_file, reports, self.checker_labels,
            self.analyzer_info)
