#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import sys
import logging

LOG = logging.getLogger('Package Tester')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.addHandler(log_handler)

info = LOG.info
debug = LOG.debug
