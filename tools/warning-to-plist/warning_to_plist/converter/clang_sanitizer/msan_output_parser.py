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
import os
import re

from ..output_parser import get_next, Message, Note, OutputParser

LOG = logging.getLogger('WarningToPlist')


class MSANOutputParser(OutputParser):
    """ Parser for Clang MemorySanitizer console outputs.

    Example output:
        ==3655==WARNING: MemorySanitizer: use-of-uninitialized-value
            #0 0x4940b3 in main /a/b/memory.cpp:7:7
            #1 0x7f3a62eaab96 in __libc_start_main (??)
            #2 0x41b2f9 in _start (??)

        Uninitialized value was stored to memory at
            #0 0x494088 in main /a/b/memory.cpp:6:16
            #1 0x7f3a62eaab96 in __libc_start_main (??)

        Uninitialized value was created by a heap allocation
            #0 0x492259 in operator new[](unsigned long) ??:48:37
            #1 0x493fec in main /a/b/memory.cpp:4:12
            #2 0x7f3a62eaab96 in __libc_start_main (??)
    """

    def __init__(self):
        super(MSANOutputParser, self).__init__()

        # Regex for parsing MemorySanitizer output message.
        self.memory_line_re = re.compile(
            # Error code
            r'==(?P<code>\d+)==WARNING: '
            # Checker name.
            r'(?P<checker>.*): '
            # Checker message.
            r'(?P<message>[\S \t]+)')

        self.memory_loc_line_re = re.compile(
            r'\s+#0 \S+ in \w+ '
            r'(?P<path>[\S ]+):(?P<line>\d+?):(?P<column>\d+)')

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        message = self.parse_sanitizer_message(it, line)
        if message:
            return message, get_next(it)

        return None, next(it)

    def parse_sanitizer_message(self, it, line):
        """ Parses MemorySanitizer output message. """
        lines = []

        # Check wheter the line is an MemorySanitizer output line.
        # Format:
        #   ==3655==WARNING: MemorySanitizer: use-of-uninitialized-value
        match = self.memory_line_re.match(line)
        if not match:
            return None

        lines.append(line)

        # Get the location of the bug.
        # Format:
        #   #0 0x4940b3 in main /a/b/memory.cpp:7:7
        line = next(it)
        loc_match = self.memory_loc_line_re.match(line)
        if not loc_match:
            return None

        # Read lines while its start with a whitespace character.
        while re.match(r'\s', line):
            lines.append(line)
            line = next(it)

        msg_path = os.path.abspath(loc_match.group('path'))
        msg_line = int(loc_match.group('line'))
        msg_col = int(loc_match.group('column'))

        return Message(
            msg_path,
            msg_line,
            msg_col,
            match.group('message').strip(),
            match.group('checker'),
            None,
            [Note(msg_path, msg_line, msg_col, ''.join(lines))])
