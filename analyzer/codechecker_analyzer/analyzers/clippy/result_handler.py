# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from pathlib import Path
from typing import Optional

from codechecker_report_converter.analyzers.clippy.analyzer_result import \
    AnalyzerResult
from codechecker_report_converter.report.parser.base import AnalyzerInfo
from codechecker_report_converter.report import error_file, report_file
from codechecker_report_converter.report.hash import get_report_hash, HashType

from codechecker_common.logger import get_logger
from codechecker_common.review_status_handler import ReviewStatusHandler
from codechecker_common.skiplist_handler import SkipListHandlers

from ..config_handler import CheckerState
from ..result_handler_base import ResultHandler


LOG = get_logger('analyzer.clippy')


class ClippyResultHandler(ResultHandler):
    """
    Create analyzer result file for Cargo/Clippy JSON output.
    """

    def __init__(self, *args, **kwargs):
        self.analyzer_info = AnalyzerInfo(name=AnalyzerResult.TOOL_NAME)
        self.clippy_analyzer_result = AnalyzerResult()
        super().__init__(*args, **kwargs)

    def postprocess_result(
        self,
        skip_handlers: Optional[SkipListHandlers],
        rs_handler: Optional[ReviewStatusHandler]
    ):
        """
        Generate CodeChecker plist output from Cargo JSON diagnostics.
        """
        LOG.debug_analyzer(self.analyzer_stdout)

        clippy_out_folder = Path(self.workspace, 'clippy')
        clippy_out_folder.mkdir(exist_ok=True)
        clippy_dest_file_name = Path(
            clippy_out_folder,
            f'{Path(self.analyzed_source_file).name}'
            f'{self.buildaction_hash}.json')

        with open(clippy_dest_file_name, 'w', encoding='utf-8') as result:
            result.write(self.analyzer_stdout)

        reports = self.clippy_analyzer_result.get_reports(clippy_dest_file_name)
        reports = [r for r in reports
                   if self.__checker_enabled(r.checker_name) and not r.skip(skip_handlers)]

        hash_type = HashType.PATH_SENSITIVE
        if self.report_hash_type == 'context-free-v2':
            hash_type = HashType.CONTEXT_FREE
        elif self.report_hash_type == 'diagnostic-message':
            hash_type = HashType.DIAGNOSTIC_MESSAGE

        for report in reports:
            report.report_hash = get_report_hash(report, hash_type)

        if rs_handler:
            reports = [r for r in reports if not rs_handler.should_ignore(r)]

        report_file.create(
            self.analyzer_result_file, reports, self.checker_labels,
            self.analyzer_info)

        error_file.update(
            self.analyzer_result_file, self.analyzer_returncode,
            self.analyzer_info, self.analyzer_cmd,
            self.analyzer_stdout, self.analyzer_stderr)

    def __checker_enabled(self, checker_name: str) -> bool:
        check_states = getattr(self, 'check_states', None)
        if check_states is None:
            return True

        if checker_name == 'clippy' or checker_name.startswith('clippy-'):
            state = check_states.get('clippy', (CheckerState.ENABLED, ''))[0]
            return state == CheckerState.ENABLED

        if checker_name == 'rustc' or checker_name.startswith('rustc-'):
            state = check_states.get('rustc', (CheckerState.ENABLED, ''))[0]
            return state == CheckerState.ENABLED

        return True
