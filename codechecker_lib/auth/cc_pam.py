# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
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

import pam
import grp
import pwd

from codechecker_lib import logger

LOG = logger.get_new_logger("PAM")


def auth_user(pam_config, username, password):
    """
    Authenticate user with PAM.
    """

    LOG.debug('Authenticating user with PAM.')

    auth = pam.pam()

    if auth.authenticate(username, password):
        allowed_users = pam_config.get("users") \
            or []
        allowed_group = pam_config.get("groups")\
            or []

        if len(allowed_users) == 0 and len(allowed_group) == 0:
            # If no filters are set, only authentication is needed.
            return True
        else:
            if username in allowed_users:
                # The user is allowed by username.
                return True

            # Otherwise, check group memeberships. If any of the user's
            # groups are an allowed groupl, the user is allowed.
            groups = [g.gr_name for g in grp.getgrall()
                      if username in g.gr_mem]
            gid = pwd.getpwnam(username).pw_gid
            groups.append(grp.getgrgid(gid).gr_name)

            return not set(groups).isdisjoint(
                set(pam_config.get("groups")))

    return False
