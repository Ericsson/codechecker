# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handler for suppressing a bug.
"""

from codechecker_lib import logger
from codechecker_lib import suppress_handler
from codechecker_lib import suppress_file_handler

# Warning! this logger should only be used in this module.
LOG = logger.get_new_logger('SUPPRESS')


class GenericSuppressHandler(suppress_handler.SuppressHandler):
    def store_suppress_bug_id(self, bug_id, file_name, comment):

        if self.suppress_file is None:
            return False

        ret = suppress_file_handler.write_to_suppress_file(self.suppress_file,
                                                           bug_id,
                                                           file_name,
                                                           comment)
        return ret

    def remove_suppress_bug_id(self, bug_id, file_name):

        if self.suppress_file is None:
            return False

        ret = suppress_file_handler.remove_from_suppress_file(
            self.suppress_file,
            bug_id,
            file_name)
        return ret
