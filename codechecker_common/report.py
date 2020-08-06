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

from codechecker_common.logger import get_logger
from codechecker_common import util

LOG = get_logger('report')


class Report(object):
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

        # Can contain the soruce line where the main section was reported.
        self.__source_line = ""

        # Dictionary containing metadata information (analyzer name, version).
        self.__metadata = metadata

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
        return self.__main['location']['file']

    @property
    def source_line(self) -> str:
        """Get the source line for the main location.

        If the source line is already set returns that
        if not tries to read it from the disk.
        """
        if not self.__source_line:
            self.__source_line = \
                util.get_line(self.__main['location']['file'], self.line)
        return self.__source_line

    @source_line.setter
    def source_line(self, sl):
        self.__source_line = sl

    @property
    def metadata(self) -> Dict:
        return self.__metadata

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
