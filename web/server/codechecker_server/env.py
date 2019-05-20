# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Environment module.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import socket
import subprocess

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def is_localhost(address):
    """
    Check if address is one of the valid values and try to get the
    IP-addresses from the system.
    """

    valid_values = ['localhost', '0.0.0.0', '*', '::1']

    try:
        valid_values.append(socket.gethostbyname('localhost'))
    except socket.herror:
        LOG.debug("Failed to get IP address for localhost.")

    try:
        valid_values.append(socket.gethostbyname(socket.gethostname()))
    except (socket.herror, socket.gaierror):
        LOG.debug("Failed to get IP address for hostname '%s'",
                  socket.gethostname())

    return address in valid_values


def call_command(command, env=None, cwd=None):
    """ Call an external command and return with (output, return_code)."""

    try:
        LOG.debug('Run %s', ' '.join(command))
        out = subprocess.check_output(command,
                                      bufsize=-1,
                                      env=env,
                                      stderr=subprocess.STDOUT,
                                      cwd=cwd)
        LOG.debug(out)
        return out, 0
    except subprocess.CalledProcessError as ex:
        LOG.debug('Running command "%s" Failed.', ' '.join(command))
        LOG.debug(str(ex.returncode))
        LOG.debug(ex.output)
        return ex.output, ex.returncode
    except OSError as oerr:
        LOG.warning(oerr.strerror)
        return oerr.strerror, oerr.errno
