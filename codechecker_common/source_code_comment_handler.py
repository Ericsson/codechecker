# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Source code comment handling.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import abc
import os
import re

from codechecker_common import util
from codechecker_common.logger import get_logger

LOG = get_logger('system')

# Note: codechecker_suppress source code comment will be also
# marked as false_positive.
SKIP_REVIEW_STATUSES = ['false_positive', 'intentional']


def skip_suppress_status(status):
    """
    Returns True if the given status is in the skip list, otherwise False.
    """
    return status in SKIP_REVIEW_STATUSES


class BaseSourceCodeCommentHandler(object):
    """ Source code handler base class. """

    __metaclass__ = abc.ABCMeta

    __suppressfile = None

    @abc.abstractmethod
    def store_suppress_bug_id(self,
                              bug_id,
                              file_name,
                              comment,
                              status):
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


class SourceCodeCommentHandler(object):
    """
    Handle source code comments.
    """
    source_code_comment_markers = [
        'codechecker_suppress',
        'codechecker_false_positive',
        'codechecker_intentional',
        'codechecker_confirmed']

    def __init__(self, source_file):
        self.__source_file = source_file

    @staticmethod
    def __check_if_comment(source_line):
        """
        Check if the line is a comment.
        Accepted comment format is only if line starts with '//'.
        """
        return source_line.strip().startswith('//')

    @staticmethod
    def __check_if_cstyle_comment(source_line):
        """
        Check if the line contains the start '/*' or
        the the end '*/' of a C style comment.
        """
        src_line = source_line.strip()
        cstyle_start = '/*' in src_line
        cstyle_end = '*/' in src_line
        return cstyle_start, cstyle_end

    def __process_source_line_comment(self, source_line_comment):
        """
        Process CodeChecker source code comment.

        Source code comments are having the following format:
           <source_code_markers> [<checker_names>] some comment

        Valid CodeChecker source code comments:
        // codechecker_suppress [all] some comment for all checkers

        // codechecker_confirmed [checker.name1] some comment

        // codechecker_confirmed [checker.name1, checker.name2] some multi
        // line comment

        Valid C style comments
        /* codechecker_suppress [all] some comment for all checkers*/

        /* codechecker_confirmed [checker.name1] some comment */

        /* codechecker_confirmed [checker.name1, checker.name2] some multi
        line comment */

        """

        # Remove extra spaces if any.
        formatted = ' '.join(source_line_comment.split())

        # Check for codechecker source code comment.
        comment_markers = '|'.join(self.source_code_comment_markers)
        pattern = r'^\s*(?P<status>' + comment_markers + r')' \
                  + r'\s*\[\s*(?P<checkers>(.*))\s*\]\s*(?P<comment>.*)$'

        ptn = re.compile(pattern)
        res = re.match(ptn, formatted)

        if res:
            checkers_names = set()
            review_status = 'false_positive'
            message = "WARNING! source code comment is missing"

            # Get checker names from suppress comment.
            checkers = res.group('checkers')
            if checkers == "all":
                checkers_names.add('all')
            else:
                suppress_checker_list = re.findall(r"[^,\s]+",
                                                   checkers.strip())
                checkers_names.update(suppress_checker_list)

            # Get comment message from suppress comment.
            comment = res.group('comment')
            if comment:
                message = comment

            # Get status from suppress comment.
            status = res.group('status')
            if status == 'codechecker_intentional':
                review_status = 'intentional'
            elif status == 'codechecker_confirmed':
                review_status = 'confirmed'

            return {'checkers': checkers_names,
                    'message': message,
                    'status': review_status}

    def has_source_line_comments(self, line):
        """
        Return True if there is any source code comment or False if not.
        """
        comments = self.get_source_line_comments(line)
        return len(comments)

    def get_source_line_comments(self, bug_line):
        """
        This function returns the available preprocessed source code comments
        for a bug line.
        """
        source_file = self.__source_file
        LOG.debug("Checking for source code comments in the source file '%s'"
                  "at line %s", self.__source_file, bug_line)

        previous_line_num = bug_line - 1

        # No more line.
        if previous_line_num < 1:
            return []

        source_line_comments = []
        curr_suppress_comment = []

        # Iterate over lines while it has comments or we reached
        # the top of the file.
        cstyle_end_found = False

        while True:

            source_line = util.get_line(source_file, previous_line_num)

            # cpp style comment
            is_comment = \
                SourceCodeCommentHandler.__check_if_comment(source_line)

            # cstyle commment
            cstyle_start, cstyle_end = \
                SourceCodeCommentHandler.__check_if_cstyle_comment(source_line)

            if not is_comment and not cstyle_start and not cstyle_end:
                if not cstyle_end_found:
                    # Not a comment
                    break

            if not cstyle_end_found and cstyle_end:
                cstyle_end_found = True

            curr_suppress_comment.append(source_line)
            has_any_marker = any(marker in source_line for marker
                                 in self.source_code_comment_markers)

            # It is a comment.
            if has_any_marker:
                rev = list(reversed(curr_suppress_comment))

                orig_review_comment = ' '.join(rev).strip()

                if rev[0].strip().startswith('//'):
                    review_comment = orig_review_comment.replace('//', '')
                else:
                    r_comment = []
                    for comment in rev:
                        comment = comment.strip()
                        comment = comment.replace('/*', '').replace('*/', '')
                        if comment.startswith('*'):
                            r_comment.append(comment[1:])
                        else:
                            r_comment.append(comment)

                    review_comment = ' '.join(r_comment).strip()

                comment = self.__process_source_line_comment(review_comment)
                if comment:
                    source_line_comments.append(comment)
                else:
                    _, file_name = os.path.split(source_file)
                    LOG.warning(
                        "Misspelled review status comment in %s@%d: %s",
                        file_name, previous_line_num, orig_review_comment)

                curr_suppress_comment = []

            if previous_line_num > 0:
                previous_line_num -= 1
            else:
                break

            if cstyle_start:
                break

        return source_line_comments

    def filter_source_line_comments(self, bug_line, checker_name):
        """
        This function filters the available source code comments for bug line
        by the checker name and returns a list of source code comments.
        Multiple cases are possible:
         - If the checker name is specified in one of the source code comment
           than this will be return.
           E.g.: // codechecker_suppress [checker.name1] some comment
             or
                /* codechecker_suppress [checker.name1] some comment */
         - If checker name is not specified explicitly in any source code
           comment bug source code comment with checker name 'all' is
           specified then this will be returned.
           E.g.: // codechecker_suppress [all] some comment
             or
                /* codechecker_suppress [all] some comment */
         - If multiple source code comments are specified with the same checker
           name then multiple source code comments will be returned.
           E.g.: // codechecker_suppress [checker.name1] some comment1
                 // codechecker_suppress [checker.name1, checker.name2] some
                 // comment1
             or
                 /* codechecker_suppress [checker.name1] some comment1
                 codechecker_suppress [checker.name1, checker.name2] some
                 comment1 */

        """
        source_line_comments = self.get_source_line_comments(bug_line)

        if not source_line_comments:
            return []

        all_checker_comment = None
        checker_name_comments = []
        for line_comment in source_line_comments:
            comment_len = len(checker_name_comments)
            if 'all' in line_comment['checkers'] and not comment_len:
                all_checker_comment = line_comment

            for c in line_comment['checkers']:
                if c in checker_name and c != 'all':
                    checker_name_comments.append(line_comment)
                    break

        if not comment_len and all_checker_comment:
            checker_name_comments.append(all_checker_comment)

        # More than one source code comment found for this line.
        if not checker_name_comments:
            LOG.debug("No source code comments are found for checker %s",
                      checker_name)
        elif len(checker_name_comments) > 1:
            LOG.debug("Multiple source code comment can be found for '%s' "
                      "checker in '%s' at line %s.", checker_name,
                      self.__source_file, bug_line)
            LOG.debug(checker_name_comments)
        else:
            LOG.debug("The following source code comment is found for"
                      "checker '%s': %s", checker_name,
                      checker_name_comments[0])
        return checker_name_comments
