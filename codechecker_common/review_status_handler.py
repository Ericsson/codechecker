# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import fnmatch
import os
from typing import List, Optional
import yaml

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

    TODO: Option 3. should also be covered by this handler class.
    """

    REVIEW_STATUS_OPTIONS = [
        'false_positive',
        'suppress',
        'confirmed',
        'intentional']

    ALLOWED_FIELDS = [
        'filepath_filter',
        'checker_filter',
        'report_hash_filter',
        'review_status',
        'message']

    def __init__(self, source_root=''):
        """
        TODO: What happens if multiple report directories are stored?
        """
        self.__review_status_yaml = None
        self.__source_root = source_root
        self.__source_comment_warnings = []
        self.__source_commets = {}
        self.__data = None

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

    def __validate_review_status_yaml_data(self):
        """
        This function validates the data read from review_status.yaml file and
        raises ValueError with the description of the error if the format is
        invalid.
        """
        if not isinstance(self.__data, list):
            raise ValueError(
                f"{self.__review_status_yaml} should be a list of review "
                "status descriptor objects.")

        for item in self.__data:
            if not isinstance(item, dict):
                raise ValueError(
                    f"Format error in {self.__review_status_yaml}: {item} "
                    "should be a review status descriptor object.")

            for field in item:
                if field not in ReviewStatusHandler.ALLOWED_FIELDS:
                    raise ValueError(
                        f"Format error in {self.__review_status_yaml}: field "
                        f"'{field}' is not allowed. Available fields are: "
                        f"{', '.join(ReviewStatusHandler.ALLOWED_FIELDS)}")

            if 'review_status' not in item:
                raise ValueError(
                    f"Format error in {self.__review_status_yaml}: "
                    f"'review_status' field is missing from {item}.")

            if item['review_status'] \
                    not in ReviewStatusHandler.REVIEW_STATUS_OPTIONS:
                raise ValueError(
                    f"Invalid review status field: {item['review_status']} at "
                    f"{item} in {self.__review_status_yaml}. Available "
                    f"options are: "
                    f"{', '.join(ReviewStatusHandler.REVIEW_STATUS_OPTIONS)}.")

            if item['review_status'] == 'suppress':
                item['review_status'] = 'false_positive'

    def get_review_status(self, report: Report) -> SourceReviewStatus:
        """
        Return the review status of the report based on source code comments.

        If the review status is not set in the source code then "unreviewed"
        review status returns. This function throws ValueError if the review
        status is ambiguous (see get_review_status_from_source()).
        """
        # 1. Check if the report has in-source review status setting.
        review_status = self.get_review_status_from_source(report)

        if review_status:
            return review_status

        # 2. Check if the report has review status setting in the yaml config.
        if self.__data:
            review_status = self.get_review_status_from_config(report)
            if review_status:
                return review_status

        # 3. Return "unreviewed" otherwise.
        return SourceReviewStatus(bug_hash=report.report_hash)

    def set_review_status_config(self, config_file):
        """
        Set the location of the review_status.yaml config file.

        When the content of multiple report directories are parsed then they
        may contain separate config files. These need to be given before
        parsing each report folders.
        """
        self.__review_status_yaml = config_file

        with open(self.__review_status_yaml,
                  encoding='utf-8', errors='ignore') as f:
            # TODO: Validate format.
            #  - Can filepath be a list?
            # TODO: May throw yaml.scanner.ScannerError.
            try:
                self.__data = yaml.safe_load(f)
            except yaml.scanner.ScannerError as err:
                raise ValueError(
                    f"Invalid YAML format in {self.__review_status_yaml}:\n"
                    f"{err}")

        self.__validate_review_status_yaml_data()

    def get_review_status_from_config(
        self,
        report: Report
    ) -> Optional[SourceReviewStatus]:
        """
        Return the review status of the given report based on the config file
        set by set_review_status_config(). If not config file set, or no
        setting matches the report then None returns.
        """
        assert self.__data is not None, \
            "Review status config file has to be set with " \
            "set_review_status_config()."

        # TODO: Document "in_source".
        for item in self.__data:
            if 'filepath_filter' in item and not fnmatch.fnmatch(
                    report.file.original_path, item['filepath_filter']):
                continue
            if 'checker_filter' in item and \
                    report.checker_name != item['checker_filter']:
                continue
            if 'report_hash_filter' in item and \
                    not report.report_hash.startswith(
                        item['report_hash_filter']):
                continue

            if any(filt in item for filt in
                   ['filepath_filter', 'checker_filter',
                    'report_hash_filter']):
                return SourceReviewStatus(
                    status=item['review_status'],
                    message=item['message']
                    .encode(encoding='utf-8', errors='ignore')
                    if 'message' in item else b'',
                    bug_hash=report.report_hash,
                    in_source=True)

        return None

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
        - If no review status belongs to the report in the source code, then
            return None.
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
