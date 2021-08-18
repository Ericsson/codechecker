# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Result handler for Clang Tidy.
"""


from codechecker_common.logger import get_logger
from codechecker_report_hash.hash import HashType, replace_report_hash

from ..result_handler_base import ResultHandler

from . import output_converter

LOG = get_logger('report')


def generate_plist_from_tidy_result(output_file, tidy_stdout):
    """
    Generate a plist file from the clang tidy analyzer results.
    """
    parser = output_converter.OutputParser()

    messages = parser.parse_messages(tidy_stdout)

    plist_converter = output_converter.PListConverter()
    plist_converter.add_messages(messages)

    plist_converter.write_to_file(output_file)


class ClangTidyPlistToFile(ResultHandler):
    """
    Create a plist file from clang-tidy results.
    """

    def postprocess_result(self):
        """
        Generate plist file which can be parsed and processed for
        results which can be stored into the database.
        """
        output_file = self.analyzer_result_file
        LOG.debug_analyzer(self.analyzer_stdout)
        tidy_stdout = self.analyzer_stdout.splitlines()
        generate_plist_from_tidy_result(output_file, tidy_stdout)

        # In the earlier versions of CodeChecker Clang Tidy never used context
        # free hash even if we enabled it with '--report-hash context-free'
        # when calling the analyze command. To do not break every hash
        # automatically when using this option we introduced a new choice for
        # --report-hash option ('context-free-v2') and we still do not use
        # context free hash for 'context-free' choice.
        if self.report_hash_type == 'context-free-v2':
            replace_report_hash(output_file, HashType.CONTEXT_FREE)
        elif self.report_hash_type == 'diagnostic-message':
            replace_report_hash(output_file, HashType.DIAGNOSTIC_MESSAGE)
