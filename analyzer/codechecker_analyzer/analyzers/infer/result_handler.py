# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Result handler for Infer.
"""
from typing import Optional
from pathlib import Path
import shutil
import os

from codechecker_report_converter.report.parser.base import AnalyzerInfo
from codechecker_report_converter.analyzers.infer.analyzer_result import \
    AnalyzerResult
from codechecker_report_converter.report import report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType

from codechecker_common.logger import get_logger
from codechecker_common.skiplist_handler import SkipListHandlers
from codechecker_common.review_status_handler import ReviewStatusHandler

from ..result_handler_base import ResultHandler

LOG = get_logger('analyzer.infer')

class InferResultHandler(ResultHandler):
    """
    Create analyzer result file for Infer output.
    """

    def __init__(self, *args, **kwargs):
        self.analyzer_info = AnalyzerInfo(name=AnalyzerResult.TOOL_NAME)
        self.infer_analyzer_result = AnalyzerResult()

        super(InferResultHandler, self).__init__(*args, **kwargs)

    def postprocess_result(
        self,
        skip_handlers: Optional[SkipListHandlers],
        rs_handler: Optional[ReviewStatusHandler]
    ):
        """
        Generate analyzer result output file which can be parsed and stored
        into the database.
        """
        LOG.debug_analyzer(self.analyzer_stdout)
        
        project_folder = Path(self.workspace).parent
        infer_out_folder = Path(self.workspace, "infer")
        infer_dest_file_name = Path(infer_out_folder, self.buildaction_hash, "report.json")

        # infer_dest_file_name = f'{self.workspace}/infer/{self.buildaction_hash}/report.json'
        # subprocess.run(f'report-converter -t fbinfer -o {self.workspace} {infer_dest_file_name}', cwd=project_folder, shell=True)

        reports = self.infer_analyzer_result.get_reports(infer_dest_file_name)

        hash_type = HashType.PATH_SENSITIVE
        if self.report_hash_type == 'context-free-v2':
            hash_type = HashType.CONTEXT_FREE
        elif self.report_hash_type == 'diagnostic-message':
            hash_type = HashType.DIAGNOSTIC_MESSAGE

        for report in reports:
            if not report.checker_name.startswith("infer-"):
                nicer_name = report.checker_name.lower().replace("_", "-")
                report.checker_name = "infer-" + nicer_name
            report.report_hash = get_report_hash(report, hash_type)

        if rs_handler:
            reports = [r for r in reports if not rs_handler.should_ignore(r)]

        report_file.create(
            self.analyzer_result_file, reports, self.checker_labels,
            self.analyzer_info)
        
        shutil.rmtree(Path(self.workspace, "infer", self.buildaction_hash))

