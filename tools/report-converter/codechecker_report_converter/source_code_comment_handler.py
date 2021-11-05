# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Source code comment handling.
"""

import json
import logging
import re

from typing import Dict, Iterable, List, Optional, Set, TextIO, Tuple

from . import util


LOG = logging.getLogger('report-converter')


REVIEW_STATUS_VALUES = ["confirmed", "false_positive", "intentional",
                        "suppress", "unreviewed"]


def contains_codechecker_comment(fp):
    """Returns true if the file content contains any
    codechecker review comments.
    The position in the object is restored where it was after the
    scanning.
    """
    pos_before_read = fp.tell()
    if pos_before_read != 0:
        fp.seek(0)
    match = re.search(".*codechecker_.*", fp.read())
    fp.seek(pos_before_read)
    if not match:
        return False
    return True


class SpellException(Exception):
    """Exception for the review comment spell errors."""
    pass


class SourceCodeComment:
    def __init__(
        self,
        checkers: Set[str],
        message: str,
        status: str,
        line: Optional[str] = None
    ):
        self.checkers = checkers
        self.message = message
        self.status = status
        self.line = line

    def to_json(self) -> Dict:
        """ Creates a JSON dictionary. """
        return {
            "checkers": list(self.checkers),
            "message": self.message,
            "status": self.status,
            "line": self.line
        }

    def __eq__(self, other) -> bool:
        if isinstance(other, SourceCodeComment):
            return self.checkers == other.checkers and \
                self.message == other.message and \
                self.status == other.status and \
                self.line == other.line

        raise NotImplementedError(
            "Comparison SourceCodeComment object with '%s' is not supported",
            type(other))

    def __repr__(self):
        return json.dumps(self.to_json())


SourceCodeComments = List[SourceCodeComment]


class SourceCodeCommentHandler:
    """
    Handle source code comments.
    """
    source_code_comment_markers = [
        'codechecker_suppress',
        'codechecker_false_positive',
        'codechecker_intentional',
        'codechecker_confirmed']

    @staticmethod
    def __check_if_comment(source_line: str) -> bool:
        """
        Check if the line is a comment.
        Accepted comment format is only if line starts with '//'.
        """
        return source_line.strip().startswith('//')

    @staticmethod
    def __check_if_cstyle_comment(source_line) -> Tuple[bool, bool]:
        """
        Check if the line contains the start '/*' or
        the the end '*/' of a C style comment.
        """
        src_line = source_line.strip()
        cstyle_start = '/*' in src_line
        cstyle_end = '*/' in src_line
        return cstyle_start, cstyle_end

    def __process_source_line_comment(
        self,
        source_line_comment: str
    ) -> Optional[SourceCodeComment]:
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
                  + r'\s*\[\s*(?P<checkers>[^\]]*)\s*\]\s*(?P<comment>.*)$'

        ptn = re.compile(pattern)
        res = re.match(ptn, formatted)

        if not res:
            return None

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

        return SourceCodeComment(checkers_names, message, review_status)

    def has_source_line_comments(self, fp: TextIO, line: int) -> bool:
        """
        Return True if there is any source code comment or False if not,
        for a given line.
        """
        try:
            comments = self.get_source_line_comments(fp, line)
        except SpellException as ex:
            # Misspell in the review status comment.
            LOG.warning(ex)
            return False
        return bool(comments)

    def scan_source_line_comments(
        self,
        fp: TextIO,
        line_numbers: Iterable[int]
    ) -> Tuple[List[Tuple[int, SourceCodeComments]], List[str]]:
        """collect all the source line review comments if exists
        in a source file at the given line numbers.

        returns a list of (line_num, comments) tuples where comments
        were found.
        """
        comments: List[Tuple[int, SourceCodeComments]] = []
        misspelled_comments: List[str] = []
        if not contains_codechecker_comment(fp):
            return comments, misspelled_comments

        line_numbers = sorted(line_numbers)
        for num in line_numbers:
            try:
                comments.append((num, self.get_source_line_comments(fp, num)))
            except SpellException as ex:
                misspelled_comments.append(str(ex))
        return comments, misspelled_comments

    def get_source_line_comments(
        self,
        fp: TextIO,
        bug_line: int
    ) -> SourceCodeComments:
        """ Returns the preprocessed source code comments for a bug line.

        raise: SpellException in case there is a spell error in the
               codechecker review comment keyword
        """
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
            source_line = util.get_linef(fp, previous_line_num)

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

                orig_review_comment = ' '.join(rev)

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

                source_line_comment = self.__process_source_line_comment(
                    review_comment)

                if source_line_comment:
                    source_line_comment.line = orig_review_comment
                    source_line_comments.append(source_line_comment)
                else:
                    orig_review_comment = orig_review_comment.strip()
                    raise SpellException(
                            f"misspelled review status comment "
                            f"@{previous_line_num}: "
                            f"{orig_review_comment.strip()}")

                curr_suppress_comment = []

            if previous_line_num > 0:
                previous_line_num -= 1
            else:
                break

            if cstyle_start:
                break

        return source_line_comments

    def filter_source_line_comments(
        self,
        fp: TextIO,
        bug_line: int,
        checker_name: str
    ) -> SourceCodeComments:
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
        source_line_comments = self.get_source_line_comments(fp, bug_line)

        if not source_line_comments:
            return []

        checker_name_comments = []
        for line_comment in source_line_comments:
            for bug_name in line_comment.checkers:
                if (bug_name in checker_name) or (bug_name == 'all'):
                    checker_name_comments.append(line_comment)

        # More than one source code comment found for this line.
        if not checker_name_comments:
            LOG.debug("No source code comments are found for checker %s",
                      checker_name)
        elif len(checker_name_comments) > 1:
            LOG.debug("Multiple source code comment can be found for '%s' "
                      "checker at line %s.", checker_name, bug_line)
            LOG.debug(checker_name_comments)
        else:
            LOG.debug("The following source code comment is found for"
                      "checker '%s': %s", checker_name,
                      checker_name_comments[0])
        return checker_name_comments
