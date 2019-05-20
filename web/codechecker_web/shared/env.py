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

import os
import stat

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def get_default_workspace():
    """
    Default workspace in the users home directory.
    """
    workspace = os.path.join(os.path.expanduser("~"), '.codechecker')
    return workspace


def get_user_input(msg):
    """
    Get the user input.

    :returns: True/False based on the asnwer from the user
    """
    return raw_input(msg).lower() in ['y', 'yes']


def check_file_owner_rw(file_to_check):
    """
    Check the file permissions.
    Return:
        True if only the owner can read or write the file.
        False if other users or groups can read or write the file.
    """
    mode = os.stat(file_to_check)[stat.ST_MODE]
    if mode & stat.S_IRGRP \
            or mode & stat.S_IWGRP \
            or mode & stat.S_IROTH \
            or mode & stat.S_IWOTH:
        LOG.warning("'%s' is readable by users other than you! "
                    "This poses a risk of leaking sensitive "
                    "information, such as passwords, session tokens, etc.!\n"
                    "Please 'chmod 0600 %s' so only you can access the file.",
                    file_to_check, file_to_check)
        return False
    return True
