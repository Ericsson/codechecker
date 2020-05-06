# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parsers for the analyzer output formats (plist ...) should create this
Report which will be stored.
"""


import json

from codechecker_common.logger import get_logger
from codechecker_common import util

LOG = get_logger('report')


class Report(object):
    """
    Just a minimal separation of the main section
    from the path section for easier skip/suppression handling
    and result processing.
    """
    def __init__(self, main, bugpath, files):
        # Dictionary containing checker name, report hash,
        # main report position, report message ...
        self.__main = main

        # Dictionary containing bug path related data
        # with control, event ... sections.
        self.__bug_path = bugpath

        # Dictionary fileid to filepath that bugpath events refer to
        self.__files = files

    @property
    def main(self):
        return self.__main

    @property
    def report_hash(self):
        return self.__main['issue_hash_content_of_line_in_context']

    @property
    def check_name(self):
        return self.__main['check_name']

    @property
    def bug_path(self):
        return self.__bug_path

    @property
    def notes(self):
        return self.__main.get('notes', [])

    @property
    def macro_expansions(self):
        return self.__main.get('macro_expansions', [])

    @property
    def files(self):
        return self.__files

    @property
    def file_path(self):
        return self.__files[self.__main['location']['file']]

    def __str__(self):
        msg = json.dumps(self.__main, sort_keys=True, indent=2)
        msg += str(self.__files)
        return msg

    def trim_path_prefixes(self, path_prefixes=None):
        """ Removes the longest matching leading path from the file paths. """
        self.__files = [util.trim_path_prefixes(file_path, path_prefixes)
                        for file_path in self.__files]

    def to_json(self):
        """ Converts to json format. """
        ret = self.__main
        ret["path"] = self.bug_path
        ret["files"] = self.files

        return ret

    def to_codeclimate(self):
        """ Convert to Code Climate format. """
        location = self.main['location']
        file_id = location['file']

        return {
            "type": "issue",
            "check_name": self.main['check_name'],
            "description": self.main['description'],
            "categories": ["Bug Risk"],
            "fingerprint": self.report_hash,
            "location": {
                "path": self.files[file_id],
                "lines": {
                    "begin": location['line']
                }
            }
        }
