# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Result handler for Clang Tidy.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from libcodechecker.analyze import tidy_output_converter
from libcodechecker.analyze.analyzers.result_handler_base \
    import ResultHandler
from libcodechecker.logger import get_logger

LOG = get_logger('report')


def generate_plist_from_tidy_result(output_file, tidy_stdout):
    """
    Generate a plist file from the clang tidy analyzer results.
    """
    parser = tidy_output_converter.OutputParser()

    messages = parser.parse_messages(tidy_stdout)

    plist_converter = tidy_output_converter.PListConverter()
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
