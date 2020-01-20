#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from ...plist_converter import PlistConverter
from .output_parser import TSANParser


class TSANPlistConverter(PlistConverter):
    """ Warning messages to plist converter. """

    TOOL_NAME = 'tsan'

    def parse_messages(self, output):
        """ Parse the given output. """
        parser = TSANParser()
        return parser.parse_messages(output)

    def _get_checker_category(self, checker):
        """ Returns the check's category."""
        return 'unknown'

    def _get_analyzer_type(self):
        """ Returns the analyzer type. """
        return self.TOOL_NAME
