# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Suppress handling.
"""

import abc
import linecache
import os
import re

from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('SUPPRESS HANDLER')


class SuppressHandler(object):
    """ Suppress handler base class. """

    __metaclass__ = abc.ABCMeta

    __suppressfile = None

    @abc.abstractmethod
    def store_suppress_bug_id(self,
                              bug_id,
                              file_name,
                              comment):
        """ Store the suppress bug_id. """
        pass

    @abc.abstractmethod
    def remove_suppress_bug_id(self,
                               bug_id,
                               file_name):
        """ Remove the suppress bug_id. """
        pass

    @property
    def suppress_file(self):
        """" File on the filesystem where the suppress
        data will be written. """
        return self.__suppressfile

    @suppress_file.setter
    def suppress_file(self, value):
        """ Set the suppress file. """
        self.__suppressfile = value

    @abc.abstractmethod
    def get_suppressed(self, bug):
        """
        Retrieve whether the given bug is suppressed according to the
        suppress handler.
        """
        pass


class SourceSuppressHandler(object):
    """
    Handle report suppression in the source.
    """

    suppress_marker = 'codechecker_suppress'

    def __init__(self, source_file, report_line, report_hash, checker_name):
        """
        Source line number indexing starts at 1.
        """

        self.__source_file = source_file
        self.__bug_line = report_line
        self.__hash_value = report_hash
        self.__checker_name = checker_name
        self.__suppressed_checkers = set()
        self.__suppress_comment = None

    def __check_if_comment(self, line):
        """
        Check if the line is a comment.
        Accepted comment format is only if line starts with '//'.
        """
        return line.strip().startswith('//')

    def __process_suppress_info(self, source_section):
        """
        Return true if suppress comment found and matches the required format.

        Accepted source suppress format only above the bug line no
        empty lines are accepted between the comment and the bug line.

        For suppressing all checker results:
        // codechecker_suppress [all] some multi line
        // comment

        For suppressing some specific checker results:
        // codechecker_suppress [checker.name1, checker.name2] some
        // multi line comment
        """
        nocomment = source_section.replace('//', '')
        # Remove extra spaces if any.
        formatted = ' '.join(nocomment.split())

        # Check for codechecker suppress comment.
        pattern = r'^\s*codechecker_suppress' \
            r'\s*\[\s*(?P<checkers>(.*))\s*\]\s*(?P<comment>.*)$'

        ptn = re.compile(pattern)

        res = re.match(ptn, formatted)

        if res:
            checkers = res.group('checkers')
            if checkers == "all":
                self.__suppressed_checkers.add('all')
            else:
                suppress_checker_list = re.findall(r"[^,\s]+",
                                                   checkers.strip())
                self.__suppressed_checkers.update(suppress_checker_list)
            comment = res.group('comment')
            if comment == '':
                self.__suppress_comment = \
                    "WARNING! suppress comment is missing"
            else:
                self.__suppress_comment = res.group('comment')
            return True
        else:
            return False

    def check_source_suppress(self):
        """
        Return true if there is a suppress comment or false if not.
        """

        source_file = self.__source_file
        LOG.debug('Checking for suppress comment in the source file: ' +
                  self.__source_file)
        previous_line_num = self.__bug_line - 1
        suppression_result = False
        if previous_line_num > 0:

            marker_found = False
            comment_line = True

            collected_lines = []

            while not marker_found and comment_line:
                source_line = linecache.getline(source_file, previous_line_num)
                if self.__check_if_comment(source_line):
                    # It is a comment.
                    if self.suppress_marker in source_line:
                        # Found the marker.
                        collected_lines.append(source_line.strip())
                        marker_found = True
                        break
                    else:
                        collected_lines.append(source_line.strip())
                        comment_line = True
                else:
                    # This is not a comment.
                    break

                if previous_line_num > 0:
                    previous_line_num -= 1
                else:
                    break

            # Collected comment lines upward from bug line.
            rev = list(reversed(collected_lines))
            if marker_found:
                suppression_result = self.__process_suppress_info(''.join(rev))

        LOG.debug('Suppress comment found: ' + str(suppression_result))
        return suppression_result

    def suppressed_checkers(self):
        """
        Get the suppressed checkers list.
        """
        return self.__suppressed_checkers

    def suppress_comment(self):
        """
        Get the suppress comment.
        """
        return self.__suppress_comment

    def get_suppressed(self):
        """ Return a (hash, filename, comment) tuple for suppressed reports and
            None for non-suppressed reports. """
        if not self.check_source_suppress():
            return

        suppress_checkers = self.suppressed_checkers()

        if self.__checker_name in suppress_checkers or \
           suppress_checkers == {'all'}:

            file_name = os.path.basename(self.__source_file)

            to_suppress = (self.__hash_value,
                           file_name,
                           self.suppress_comment())

            LOG.debug(to_suppress)

            return to_suppress
