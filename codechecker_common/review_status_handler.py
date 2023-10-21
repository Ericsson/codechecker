# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import os
from typing import List, Optional

from codechecker_report_converter.report import Report, SourceReviewStatus
from codechecker_common.logger import get_logger
from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler, SpellException, contains_codechecker_comment, \
    SourceCodeComment, SourceCodeComments


LOG = get_logger('system')


class ReviewStatusHandler:
    """
    This class helps to determine the review status of a report. The review
    status may come either from several sources:

    1. Source code comment:
        // codechecker_suppress [core.DivideZero] This is a false positive.
    2. Review status configuration file:
        <report_folder>/review_status.yaml contains review status settings on
        file path or bug has granularity.
    3. Review status rule:
        A mapping between bug hashes and review statuses set in the GUI.

    TODO: Option 2. will be handled in a future commit.
    TODO: Option 3. should also be covered by this handler class.
    """
    def __init__(self, source_root=''):
        self.__source_root = source_root
        self.__source_comment_warnings = []
        self.__source_commets = {}

    def __parse_codechecker_review_comment(
        self,
        source_file_name: str,
        report_line: int,
        checker_name: str
    ) -> SourceCodeComments:
        """Parse the CodeChecker review comments from a source file at a given
        position.  Returns an empty list if there are no comments.
        """
        src_comment_data = []
        with open(source_file_name, encoding='utf-8', errors='ignore') as f:
            if contains_codechecker_comment(f):
                sc_handler = SourceCodeCommentHandler()
                try:
                    src_comment_data = sc_handler.filter_source_line_comments(
                        f, report_line, checker_name)
                except SpellException as ex:
                    self.__source_comment_warnings.append(
                        f"{source_file_name} contains {ex}")

        return src_comment_data

    def get_review_status(self, report: Report) -> SourceReviewStatus:
        """
        Return the review status of the report based on source code comments.

        If the review status is not set in the source code then "unreviewed"
        review status returns. This function throws ValueError if the review
        status is ambiguous (see get_review_status_from_source()).
        """
        rs_from_source = self.get_review_status_from_source(report)

        if rs_from_source:
            return rs_from_source

        return SourceReviewStatus(bug_hash=report.report_hash)

    def get_review_status_from_source(
        self,
        report: Report
    ) -> Optional[SourceReviewStatus]:
        """
        Return the review status based on the source code comment belonging to
        the given report.

        - Return the review status if it is set in the source code.
        - If the review status is ambiguous (i.e. multiple source code
            comments belong to it) then a ValueError exception is raised which
            contains information about the problem in a string.
        - If the soure file changed (which means that the source comments may
            have replaced, changed or removed) then None returns.
        TODO: This function either returns a SourceReviewStatus, or raises an
        exception or returns None. This is too many things that a caller needs
        to handle. The reason is that according to the current behaviors,
        ambiguous comment results a hard error, and changed files result a
        warning with "unreviewed" status. In the future we could implement a
        logic where we take the first comment into account in case of ambiguity
        or return "unreviewed" with a warning, like changed files.
        """
        # The original file path is needed here, not the trimmed, because
        # the source files are extracted as the original file path.
        # TODO: Should original_path be strip('/') at store?
        source_file_name = os.path.realpath(os.path.join(
            self.__source_root, report.file.original_path))

        if source_file_name in report.changed_files:
            return None

        if os.path.isfile(source_file_name):
            src_comment_data = self.__parse_codechecker_review_comment(
                source_file_name, report.line, report.checker_name)

            if len(src_comment_data) == 1:
                data = src_comment_data[0]
                status, message = data.status, data.message
                self.__source_commets[report] = data

                return SourceReviewStatus(
                    status=status,
                    message=message.encode('utf-8'),
                    bug_hash=report.report_hash,
                    in_source=True)
            elif len(src_comment_data) > 1:
                raise ValueError(
                    f"Multiple source code comments can be found for "
                    f"'{report.checker_name}' checker in '{source_file_name}' "
                    f"at line {report.line}.")

        return None

    def source_comment_warnings(self) -> List[str]:
        """
        Sometimes it is not intuitive why the given review status is determined
        for a report. For example, if an in-source suppression is misspelled,
        then the report remains unreviewed:
        // codechecker_suppresssss [<checker name>] comment
        This function returns a list of warning messages on these unintuitive
        behaviors.
        """
        return self.__source_comment_warnings

    def source_comment(self, report: Report) -> Optional[SourceCodeComment]:
        """
        This ReviewStatusHandler class is caching source comments so they are
        read and parsed only once for each report.
        """
        return self.__source_commets.get(report)
