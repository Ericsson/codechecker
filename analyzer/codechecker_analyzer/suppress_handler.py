# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handler for suppressing a bug.
"""

from codechecker_report_converter.report import Report

from codechecker_analyzer import suppress_file_handler
from codechecker_common.logger import get_logger

# Warning! this logger should only be used in this module.
LOG = get_logger('system')


class GenericSuppressHandler:

    def __init__(self, suppress_file, allow_write, src_comment_status_filter):
        """
        Create a new suppress handler with a suppress_file as backend.
        """
        self.__suppress_info = []
        self.__allow_write = allow_write
        self.src_comment_status_filter = src_comment_status_filter or []

        if suppress_file:
            self.suppress_file = suppress_file
            self.__have_memory_backend = True
            self.__revalidate_suppress_data()
        else:
            self.__have_memory_backend = False

            if allow_write:
                raise ValueError("Can't create allow_write=True suppress "
                                 "handler without a backend file.")

    @property
    def suppress_file(self):
        """" File on the filesystem where the suppress
        data will be written. """
        return self.__suppressfile

    @suppress_file.setter
    def suppress_file(self, value):
        """ Set the suppress file. """
        self.__suppressfile = value

    def __revalidate_suppress_data(self):
        """Reload the information in the suppress file to the memory."""

        if not self.__have_memory_backend:
            # Do not load and have suppress data stored in memory if not
            # needed.
            return

        with open(self.suppress_file, 'r',
                  encoding='utf-8', errors='ignore') as file_handle:
            self.__suppress_info = suppress_file_handler.\
                get_suppress_data(file_handle)

    def store_suppress_bug_id(self, bug_id, file_name, comment, status):

        if not self.__allow_write:
            return True
        ret = suppress_file_handler.write_to_suppress_file(
                self.suppress_file,
                bug_id,
                file_name,
                comment,
                status)
        self.__revalidate_suppress_data()
        return ret

    def skip_suppress_status(self, status) -> bool:
        """ Returns True if the given status should be skipped. """
        if not self.src_comment_status_filter:
            return False

        return status not in self.src_comment_status_filter

    def get_suppressed(self, report: Report) -> bool:
        """ True if the given report is suppressed. """
        return any([suppress for suppress in self.__suppress_info
                    if suppress[0] == report.report_hash and
                    suppress[1] == report.file.name and
                    self.skip_suppress_status(suppress[3])])
