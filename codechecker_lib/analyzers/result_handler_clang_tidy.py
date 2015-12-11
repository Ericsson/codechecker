# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import ntpath

import shared

from codechecker_lib import logger
from codechecker_lib import tidy_output_converter

from codechecker_lib.analyzers import result_handler_store_db
from codechecker_lib.analyzers import result_handler_printout

from codechecker_lib.analyzers import result_handler_base

LOG = logger.get_new_logger('CLANG_TIDY_RESULT_HANDLER')


class CTDBResHandler(result_handler_store_db.ResultHandlerStoreToDB):
    """
    Clang tidy results database handler
    """

    def postprocess_result(self):
        """

        """
        parser = tidy_output_converter.OutputParser()

        messages = parser.parse_messages(self.analyzer_stdout.splitlines())

        plist_converter = tidy_output_converter.PListConverter()
        plist_converter.add_messages(messages)

        plist = self.get_analyzer_result_file()
        plist_converter.write_to_file(plist)


class CTQCResHandler(result_handler_printout.ResultHandlerPrintOut):
    """

    """

    def postprocess_result(self, result):
        parser = tidy_output_converter.OutputParser()

        messages = parser.parse_messages(self.analyzer_stdout.splitlines())

        plist_converter = tidy_output_converter.PListConverter()
        plist_converter.add_messages(messages)

        plist = self.get_analyzer_result_file()
        plist_converter.write_to_file(plist)
