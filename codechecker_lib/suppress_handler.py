# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
suppress handling
'''

import re
import abc
import linecache

from codechecker_lib import logger

LOG = logger.get_new_logger('SUPPRESS HANDLER')


class SuppressHandler(object):
    """ suppress handler base class """

    __metaclass__ = abc.ABCMeta

    __suppressfile = None

    @abc.abstractmethod
    def store_suppress_bug_id(self,
                              source_file_path,
                              bug_id,
                              hash_type,
                              file_name,
                              comment):
        """ store the suppress bug_id """
        pass

    @abc.abstractmethod
    def remove_suppress_bug_id(self,
                               bug_id,
                               hash_type,
                               file_name):
        """ remove the suppress bug_id """
        pass

    @property
    def suppress_file(self):
        """" file on the filesystem where the suppress
        data will be written """
        return self.__suppressfile

    @suppress_file.setter
    def suppress_file(self, value):
        """ set the suppress file"""
        self.__suppressfile = value


class SourceSuppressHandler(object):
    """
    handle bug suppression in the source
    """

    suppress_marker = 'codechecker_suppress'

    def __init__(self, source_file, bug_line):
        self.__source_file = source_file
        self.__bug_line = bug_line
        self.__suppressed_checkers = []
        self.__suppress_comment = None

    def __check_if_comment(self, line):
        """
        check if the line is a comment
        accepted comment format is only if line starts with '//'
        """
        return line.strip().startswith('//')

    def __process_suppress_info(self, source_section):
        """
        return true if suppress comment found and matches the
        required format

        Accepted source suppress format only above the bug line no
        empty lines are accepted between the comment and the bug line

        For suppressing all checker results:
        // codechecker_suppress [all] some multi line
        // comment

        For suppressing some specific checker results:
        // codechecker_suppress [checker.name1, checker.name2] some
        // multi line comment
        """
        nocomment = source_section.replace('//', '')
        # remove extra spaces if any
        formatted = ' '.join(nocomment.split())

        # check for codechecker suppress comment
        pattern = r'^\s*codechecker_suppress\s*\[\s*(?P<checkers>(.*))\s*\]\s*(?P<comment>.*)$'

        ptn = re.compile(pattern)

        res = re.match(ptn, formatted)

        if res:
            checkers = res.group('checkers')
            if checkers == "all":
                self.__suppressed_checkers.append('all')
            else:
                suppress_checker_list = re.findall(r"[^,\s]+", checkers.strip())
                self.__suppressed_checkers.extend(suppress_checker_list)
            comment = res.group('comment')
            if comment == '':
                self.__suppress_comment = "WARNING! suppress comment is missing"
            else:
                self.__suppress_comment = res.group('comment')
            return True
        else:
            return False

    def check_source_suppress(self):
        """
        return true if there is a suppress comment or false if not
        """

        source_file = self.__source_file
        LOG.debug('Checking for suppress comment in the source file: '
                  + self.__source_file)
        previous_line_num = self.__bug_line - 1
        suppression_result = False
        if previous_line_num > 0:

            marker_found = False
            comment_line = True

            collected_lines = []

            while (not marker_found and comment_line):
                source_line = linecache.getline(source_file, previous_line_num)
                if(self.__check_if_comment(source_line)):
                    # it is a comment
                    if self.suppress_marker in source_line:
                        # found the marker
                        collected_lines.append(source_line.strip())
                        marker_found = True
                        break
                    else:
                        collected_lines.append(source_line.strip())
                        comment_line = True
                else:
                    # this is not a comment
                    comment_line = False
                    break

                if(previous_line_num > 0):
                    previous_line_num -= 1
                else:
                    break

            # collected comment lines upward from bug line
            rev = list(reversed(collected_lines))
            if marker_found:
                suppression_result = self.__process_suppress_info(''.join(rev))

        LOG.debug('Suppress comment found: ' + str(suppression_result))
        return suppression_result

    def suppressed_checkers(self):
        """
        get the suppressed checkers list
        """
        return self.__suppressed_checkers

    def suppress_comment(self):
        """
        get the suppress comment
        """
        return self.__suppress_comment
