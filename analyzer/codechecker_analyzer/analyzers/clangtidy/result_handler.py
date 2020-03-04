# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Result handler for Clang Tidy.
"""


from codechecker_common import report
from codechecker_common.logger import get_logger

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

        if self.report_hash_type == 'context-free':
            report.use_context_free_hashes(output_file)
