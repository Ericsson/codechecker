# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import re

from ..parser import SANParser

LOG = logging.getLogger('report-converter')


class Parser(SANParser):
    """ Parser for Clang AddressSanitizer console outputs. """

    checker_name = "AddressSanitizer"

    # Regex for parsing AddressSanitizer output message.
    line_re = re.compile(
            # Error code
            r'==(?P<code>\d+)==(ERROR|WARNING): AddressSanitizer: '
            # Checker message.
            r'(?P<message>[\S \t]+)')
