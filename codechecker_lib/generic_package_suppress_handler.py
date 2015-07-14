# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
handler for suppressing a bug
'''

from codechecker_lib import logger
from codechecker_lib import suppress_handler
from codechecker_lib import suppress_file_handler

# Warning! this logger should only be used in this module
LOG = logger.get_new_logger('SUPPRESS')


class GenericSuppressHandler(suppress_handler.SuppressHandler):

    def store_suppress_bug_id(self, source_file_path, bug_id, hash_type, comment):

        if self.suppress_file is None:
            return True

        ret = suppress_file_handler.write_to_suppress_file(self.suppress_file,
                                                           bug_id, hash_type,
                                                           comment)
        return ret

    def remove_suppress_bug_id(self, source_file_path, bug_id, hash_type):

        if self.suppress_file is None:
            return True

        ret = suppress_file_handler.remove_from_suppress_file(self.suppress_file,
                                                              bug_id, hash_type)
        return ret

    def store_suppress_path(self, source_file_path, path, comment):

        if self.suppress_file is None:
            return True

        ret = suppress_file_handler.write_to_suppress_file(self.suppress_file,
                                                           path, comment)
        return ret
