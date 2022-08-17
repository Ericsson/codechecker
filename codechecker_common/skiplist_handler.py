# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
"""


import fnmatch
import re
import os

from codechecker_common.logger import get_logger

LOG = get_logger('system')


class SkipListHandler:
    """
    Skiplist file format:

    -/skip/all/source/in/directory*
    -/do/not/check/this.file
    +/dir/check.this.file
    -/dir/*
    """

    def __init__(self, skip_file_content=""):
        """
        Process the lines of the skip file.
        """
        self.__skip = []
        if not skip_file_content:
            skip_file_content = ""

        self.__skip_file_lines = [line.strip() for line
                                  in skip_file_content.splitlines()
                                  if line.strip()]

        valid_lines = self.__check_line_format(self.__skip_file_lines)
        self.__gen_regex(valid_lines)

    def __gen_regex(self, skip_lines):
        """
        Generate a regular expression from the given skip lines
        and collect them for later match.

        The lines should be checked for validity before generating
        the regular expressions.
        """
        for skip_line in skip_lines:
            norm_skip_path = os.path.normpath(skip_line[1:].strip())
            rexpr = re.compile(
                fnmatch.translate(norm_skip_path + '*'))
            self.__skip.append((skip_line, rexpr))

    def __check_line_format(self, skip_lines):
        """
        Check if the skip line is given in a valid format.
        Returns the list of valid lines.
        """
        valid_lines = []
        for line in skip_lines:
            if len(line) < 2 or line[0] not in ['-', '+']:
                LOG.warning("Skipping malformed skipfile pattern: %s", line)
                continue

            valid_lines.append(line)

        return valid_lines

    @property
    def skip_file_lines(self):
        """
        List of the lines from the skip file without changes.
        """
        return self.__skip_file_lines

    def overwrite_skip_content(self, skip_lines):
        """
        Cleans out the already collected skip regular expressions
        and rebuilds the list from the given skip_lines.
        """
        self.__skip = []
        valid_lines = self.__check_line_format(skip_lines)
        self.__gen_regex(valid_lines)

    def should_skip(self, source):
        """
        Check if the given source should be skipped.
        Should the analyzer skip the given source file?
        """
        if not self.__skip:
            return False

        for line, rexpr in self.__skip:
            if rexpr.match(source):
                sign = line[0]
                return sign == '-'
        return False

    def __call__(self, source_file_path: str) -> bool:
        """
        Check if the given source should be skipped.
        """
        return self.should_skip(source_file_path)


class SkipListHandlers(list):
    def should_skip(self, file_path: str):
        """
        True if the given source should be skipped by any of the skip list
        handler.
        """
        return any(handler.should_skip(file_path) for handler in self)

    # FIXME: eliminate this function and use should_skip instead of this.
    # Do the same in the SkipListHandler class above.
    def __call__(self, file_path: str) -> bool:
        """
        Check if the given source should be skipped.
        """
        return self.should_skip(file_path)
