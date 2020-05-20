# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Check host machine for a compile command logger.
"""


import errno
import subprocess

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def check_intercept(env):
    """
    Simple check if intercept (scan-build-py) is available.
    """
    intercept_cmd = ['intercept-build', '--help']
    try:
        res = subprocess.check_call(
            intercept_cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            errors="ignore")

        if not res:
            return True
        else:
            LOG.debug('Failed to run: "%s"', ' '.join(intercept_cmd))
            return False
    except subprocess.CalledProcessError:
        LOG.debug('Failed to run: "%s", process returned non-zero exit code.',
                  ' '.join(intercept_cmd))
        return False
    except OSError as oerr:
        if oerr.errno == errno.ENOENT:
            # Not just intercept-build can be used for logging.
            # It is possible that another build logger is available.
            LOG.debug(oerr)
            LOG.debug('Failed to run: "%s"', ' '.join(intercept_cmd))
            return False
