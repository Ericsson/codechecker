# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Temporary directory module.
"""


import datetime
import os

from codechecker_common.hash import md5
from codechecker_common.logger import get_logger

LOG = get_logger('system')


def get_tmp_dir_hash():
    """Generate a hash based on the current time and process id."""

    pid = os.getpid()
    time = datetime.datetime.now()

    data = str(pid) + str(time)

    dir_hash = md5(data.encode("utf-8")).hexdigest()

    LOG.debug('The generated temporary directory hash is %s.', dir_hash)

    return dir_hash
