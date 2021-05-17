# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Parsers for the analyzer output formats (plist ...) should create this
type of Report which will be printed or stored.
"""

from typing import Dict, List
import json
import os

from codechecker_common.logger import get_logger
from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler, SpellException
from codechecker_common import util

LOG = get_logger('report')


class Report:
    """Represents an analyzer report.

    The main section is where the analyzer reported the issue.
    The bugpath contains additional locations (and messages) which lead to
    the main section.
    """

    def __init__(self,
                 main: Dict,
                 bugpath: Dict,
                 files: Dict[int, str],
                 metadata: Dict[str, str]):

        # Dictionary containing checker name, report hash,
        # main report position, report message ...
        self.__main = main

        # Dictionary containing bug path related data
        # with control, event ... sections.
        self.__bug_path = bugpath

        # Dictionary fileid to filepath that bugpath events refer to
        self.__files = files

        # Can contain the source line where the main section was reported.
        self.__source_line = ""

        # Dictionary containing metadata information (analyzer name, version).
        self.__metadata = metadata

        self.__source_code_comments = None
        self.__sc_handler = SourceCodeCommentHandler()

    @property
    def line(self) -> int:
        return self.__main['location']['line']

    @property
    def col(self) -> int:
        return self.__main['location']['col']

    @property
    def description(self) -> str:
        return self.__main['description']

    @property
    def main(self) -> Dict:
        return self.__main

    @property
    def report_hash(self) -> str:
        return self.__main['issue_hash_content_of_line_in_context']

    @property
    def check_name(self) -> str:
        return self.__main['check_name']

    @property
    def bug_path(self) -> Dict:
        return self.__bug_path

    @property
    def notes(self) -> List[str]:
        return self.__main.get('notes', [])

    @property
    def macro_expansions(self) -> List[str]:
        return self.__main.get('macro_expansions', [])

    @property
    def files(self) -> Dict[int, str]:
        return self.__files

    @property
    def file_path(self) -> str:
        """ Get the filepath for the main report location. """
        return self.files[self.__main['location']['file']]

    @property
    def source_line(self) -> str:
        """Get the source line for the main location.

        If the source line is already set returns that
        if not tries to read it from the disk.
        """
        if not self.__source_line:
            self.__source_line = util.get_line(self.file_path, self.line)

        return self.__source_line

    @source_line.setter
    def source_line(self, sl):
        self.__source_line = sl

    @property
    def metadata(self) -> Dict:
        return self.__metadata

    @property
    def source_code_comments(self):
        """
        Get source code comments for the report.
        It will read the source file only once.
        """
        if self.__source_code_comments is not None:
            return self.__source_code_comments

        self.__source_code_comments = []

        if not os.path.exists(self.file_path):
            return self.__source_code_comments

        with open(self.file_path, encoding='utf-8', errors='ignore') as sf:
            try:
                self.__source_code_comments = \
                    self.__sc_handler.filter_source_line_comments(
                        sf, self.line, self.check_name)
            except SpellException as ex:
                LOG.warning("%s contains %s", os.path.basename(self.file_path),
                            str(ex))

        if len(self.__source_code_comments) == 1:
            LOG.debug("Report %s is suppressed in code. file: %s Line %s",
                      self.report_hash, self.file_path, self.line)
        elif len(self.__source_code_comments) > 1:
            LOG.warning(
                "Multiple source code comment can be found "
                "for '%s' checker in '%s' at line %s. "
                "This bug will not be suppressed!",
                self.check_name, self.file_path, self.line)

        return self.__source_code_comments

    def check_source_code_comments(self, comment_types: List[str]):
        """
        True if it doesn't have a source code comment or if every comments have
        specified comment types.
        """
        if not self.source_code_comments:
            return True

        return all(c['status'] in comment_types
                   for c in self.source_code_comments)

    def __str__(self):
        msg = json.dumps(self.__main, sort_keys=True, indent=2)
        msg += str(self.__files)
        return msg

    def trim_path_prefixes(self, path_prefixes=None):
        """ Removes the longest matching leading path from the file paths. """
        self.__files = {i: util.trim_path_prefixes(file_path, path_prefixes)
                        for i, file_path in self.__files.items()}

    def to_json(self):
        """Converts to a special json format.

        This format is used by the parse command when the reports are printed
        to the stdout in json format."""
        ret = self.__main
        ret["path"] = self.bug_path
        ret["files"] = self.files.values()

        return ret
