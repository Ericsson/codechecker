# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------


def has_flag(flag, cmd):
    """Return true if a cmd contains a flag or false if not."""
    return bool(next((x for x in cmd if x.startswith(flag)), False))
