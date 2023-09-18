# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


from dataclasses import dataclass
from datetime import datetime
import os
from typing import Optional

from logger import get_logger
from codechecker_report_converter.report import Report
from codechecker_report_converter.source_code_comment_handler import \
    SourceCodeCommentHandler, SpellException, contains_codechecker_comment, \
    SourceCodeComments


LOG = get_logger('system')


@dataclass
class SourceReviewStatus:
    """
    Helper class for handling in source review statuses.
    Collect the same info as a review status rule.

    TODO: rename this class, because this not only represents review statuses
          in source code comments but in review status yaml too.
    """
    status: str = "unreviewed"
    message: bytes = b""
    bug_hash: str = ""
    in_source: bool = False
    author: Optional[str] = None
    date: Optional[datetime] = None


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
    def __init__(self, source_root):
        self.__source_root = source_root

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
                    LOG.warning("File %s contains %s", source_file_name, ex)

        return src_comment_data

    def get_review_status_from_source(
        self,
        report: Report
    ) -> SourceReviewStatus:
        """
        Return the review status set in the source code belonging to
        the given report.

        - Return the review status if it is set in the source code.
        - If the review status is ambiguous (i.e. multiple source code
            comments belong to it) then a ValueError exception is raised which
            contains information about the problem in a string.
        # TODO: If not found then return None or unreviewed by default?
        """
        # The original file path is needed here, not the trimmed, because
        # the source files are extracted as the original file path.
        source_file_name = os.path.realpath(os.path.join(
            self.__source_root, report.file.original_path.strip("/")))

        if os.path.isfile(source_file_name):
            src_comment_data = self.__parse_codechecker_review_comment(
                source_file_name, report.line, report.checker_name)

            if len(src_comment_data) == 1:
                data = src_comment_data[0]
                status, message = data.status, bytes(data.message, 'utf-8')

                review_status = SourceReviewStatus(
                    status=status,
                    message=message,
                    bug_hash=report.report_hash,
                    in_source=True
                )

                return review_status
            elif len(src_comment_data) > 1:
                LOG.warning(
                    "Multiple source code comment can be found "
                    "for '%s' checker in '%s' at line %s. "
                    "This suppression will not be taken into account!",
                    report.checker_name, source_file_name, report.line)

                raise ValueError(
                    f"{source_file_name}|{report.line}|{report.checker_name}")

        # A better way to handle reports where the review status is not
        # set in the source is to return None, and set the reviews status info
        # at report addition time.
        return SourceReviewStatus(
            status="unreviewed",
            message=b'',
            bug_hash=report.report_hash,
            in_source=False
        )

