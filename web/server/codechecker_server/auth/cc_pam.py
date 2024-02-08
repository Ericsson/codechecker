# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
PAM authentication modul for Codechecker.

Example configuration for PAM based authentication.

"method_pam": {
  "enabled" : true,
  "users": [
    "root", "myname"
  ],
  "groups": [
    "adm", "cc-users"
  ]
}

"""


import grp
import pam
import pwd
from typing import List

from codechecker_common.logger import get_logger

LOG = get_logger('server')


def auth_user(pam_config, username, password) -> bool:
    """
    Authenticate user with PAM.
    """

    LOG.debug('Authenticating user with PAM.')

    auth = pam.pam()

    if auth.authenticate(username, password):
        allowed_users: List[str] = pam_config.users
        allowed_groups: List[str] = pam_config.groups

        if not allowed_users and not allowed_groups:
            # If no filters are set, only authentication is needed.
            return True

        if username in allowed_users:
            return True

        # Otherwise, check group memeberships. If any of the user's groups is
        # an allowed group, the user is allowed.
        groups = {g.gr_name for g in grp.getgrall() if username in g.gr_mem}
        gid = pwd.getpwnam(username).pw_gid
        groups.add(grp.getgrgid(gid).gr_name)

        return not groups.isdisjoint(allowed_groups)

    return False
