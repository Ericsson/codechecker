# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from codechecker_lib import logger
from codechecker_lib import tidy_output_converter

from codechecker_lib.analyzers.result_handler_plist_to_db import PlistToDB
from codechecker_lib.analyzers.result_handler_plist_to_stdout import PlistToStdout

LOG = logger.get_new_logger('CLANG_TIDY_RESULT_HANDLER')


def generate_plist_from_tidy_result(output_file, tidy_stdout):
    """
    Generate a plist file from the clang tidy analyzer results
    """
    parser = tidy_output_converter.OutputParser()

    messages = parser.parse_messages(tidy_stdout)

    plist_converter = tidy_output_converter.PListConverter()
    plist_converter.add_messages(messages)

    plist_converter.write_to_file(output_file)


class ClangTidyPlistToDB(PlistToDB):
    """
    Store clang tidy plist results to a database
    """

    def postprocess_result(self):
        """
        Generate plist file which can be parsed and processed for
        results which can be stored into the database
        """
        output_file = self.get_analyzer_result_file()
        tidy_stdout = self.analyzer_stdout.splitlines()
        generate_plist_from_tidy_result(output_file, tidy_stdout)


class ClangTidyPlistToStdout(PlistToStdout):
    """
    Print the clang tidy results to the standatd output
    """

    def postprocess_result(self):
        """
        For the same output format with the clang static analyzer the
        Clang tidy results are postprocessed into a plist file
        """

        output_file = self.get_analyzer_result_file()
        tidy_stdout = self.analyzer_stdout.splitlines()
        generate_plist_from_tidy_result(output_file, tidy_stdout)
