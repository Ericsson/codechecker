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
import re

from ...output_parser import get_next, Message, Event
from ..output_parser import SANParser

LOG = logging.getLogger('ReportConverter')


class ASANParser(SANParser):
    """ Parser for Clang AddressSanitizer console outputs. """

    def __init__(self):
        super(ASANParser, self).__init__()

        # Regex for parsing AddressSanitizer output message.
        self.address_line_re = re.compile(
            # Error code
            r'==(?P<code>\d+)==(ERROR|WARNING): AddressSanitizer: '
            # Checker message.
            r'(?P<message>[\S \t]+)')

    def parse_sanitizer_message(self, it, line):
        """ Parses AddressSanitizer output message.

        The first event will be the main location of the bug.
        """
        match = self.address_line_re.match(line)
        if not match:
            return None, line

        line = get_next(it)
        stack_traces, events, line = self.parse_stack_trace(it, line)

        if not events:
            return None, line

        notes = [Event(events[0].path, events[0].line, events[0].column,
                       ''.join(stack_traces))]

        return Message(events[0].path, events[0].line, events[0].column,
                       match.group('message').strip(),
                       "AddressSanitizer",
                       events, notes), line
