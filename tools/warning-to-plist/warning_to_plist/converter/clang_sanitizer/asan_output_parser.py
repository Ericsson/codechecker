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


class ASANOutputParser(OutputParser):
    """ Parser for Clang AddressSanitizer console outputs.

    Example output:
        ==20851==ERROR: AddressSanitizer: heap-use-after-free on address...
        READ of size 4 at 0x614000000044 thread T0
            #0 0x4f4c95 in main /a/b/main.cpp:4:10
            #1 0x7fb2a0078b96 in __libc_start_main (??)
            #2 0x41ab59 in _start (??)

        0x614000000044 is located 4 bytes inside of 400-byte region...
        freed by thread T0 here:
            #0 0x4f29c2 in operator delete[](void*) ??:170:3
            #1 0x4f4b9e in main /a/b/main.cpp:3:3
            #2 0x7fb2a0078b96 in __libc_start_main (??)

        previously allocated by thread T0 here:
            #0 0x4f1d92 in operator new[](unsigned long) ??:109:3
            #1 0x4f4b3c in main /a/b/main.cpp:2:16
            #2 0x7fb2a0078b96 in __libc_start_main (??)
    """

    def __init__(self):
        super(ASANOutputParser, self).__init__()

        # Regex for parsing AddressSanitizer output message.
        self.address_line_re = re.compile(
            # Error code
            r'==(?P<code>\d+)==ERROR: '
            # Checker name.
            r'(?P<checker>.*): '
            # Checker message.
            r'(?P<message>[\S \t]+)')

        self.address_read_line_re = re.compile(
            r'READ of size \d+ at \S+ thread \S+')

        self.address_read_loc_line_re = re.compile(
            r'\s+#0 \S+ in \w+ '
            r'(?P<path>[\S ]+):(?P<line>\d+?):(?P<column>\d+)')

        self.address_located_line_re = re.compile(
            r'\S+ is located \d+ bytes inside of \d+-byte region \S+')

        self.address_freed_line_re = re.compile(
            r'freed by thread \S+ here:')

        self.address_prev_alloc_line_re = re.compile(
            r'previously allocated by thread \S+ here:')

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
        """ Parses AddressSanitizer output message. """
        lines = []

        # Check wheter the line is an AddressSanitizer output line.
        # Format:
        #   ==20851==ERROR: AddressSanitizer: heap-use-after-free on address...
        match = self.address_line_re.match(line)
        if not match:
            return None

        lines.append(line)

        # Check wheter the line is an AddressSanitizer READ output line.
        # Format:
        #   READ of size 4 at 0x614000000044 thread T0
        line = next(it)
        line_match = self.address_read_line_re.match(line)
        if not line_match:
            return None

        lines.append(line)

        # Get the location of the bug.
        # Format:
        #   #0 0x4f4c95 in main /a/b/main.cpp:4:10
        line = next(it)
        loc_match = self.address_read_loc_line_re.match(line)
        if not loc_match:
            return None

        lines.append(line)

        # Read lines while its start with a whitespace character.
        while re.match(r'\s', line):
            lines.append(line)
            line = next(it)

        # Read further lines of the AddressSanitizer output.
        line_notes_re = [self.address_located_line_re,
                         self.address_freed_line_re,
                         self.address_prev_alloc_line_re]

        for line_re in line_notes_re:
            if not line_re.match(line):
                break
            lines.append(line)

            line = next(it)
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
