# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import errno
import os
import subprocess

from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('HOST CHECK')


def check_intercept(env):
    """
    Simple check if intercept (scan-build-py) is available.
    """
    intercept_cmd = ['intercept-build']
    try:
        with open(os.devnull, 'wb') as null:
            res = subprocess.check_call(intercept_cmd,
                                        env=env,
                                        stdout=null,
                                        stderr=null)

        if not res:
            return True
        else:
            LOG.debug('Failed to run: "' + ' '.join(intercept_cmd) + '"')
            return False
    except subprocess.CalledProcessError:
        LOG.debug('Failed to run: "' + ' '.join(intercept_cmd) + '", process '
                  'returned non-zero exit code.')
        return False
    except OSError as oerr:
        if oerr.errno == errno.ENOENT:
            # Not just intercept-build can be used for logging.
            # It is possible that another build logger is available.
            LOG.debug(oerr)
            LOG.debug('Failed to run: "' + ' '.join(intercept_cmd) + '"')
            return False
