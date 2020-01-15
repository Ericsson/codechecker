#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging

from ..output_parser import OutputParser

from .asan_output_parser import ASANOutputParser
from .msan_output_parser import MSANOutputParser
from .ubsan_output_parser import UBSANOutputParser

LOG = logging.getLogger('ReportConverter')


class ClangSanitizerOutputParser(OutputParser):
    """ Parser for Clang Sanitizer console outputs. """

    def __init__(self):
        super(ClangSanitizerOutputParser, self).__init__()

        self.sanitizer_parsers = [ASANOutputParser(),
                                  MSANOutputParser(),
                                  UBSANOutputParser()]

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        for san_parser in self.sanitizer_parsers:
            message, next_line = san_parser.parse_sanitizer_message(it, line)
            if message:
                return message, next_line

        return None, next(it)
