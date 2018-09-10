# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
This module stores constants that are shared between the CodeChecker server
and client, related to API and other version-specific information.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

# The name of the cookie which contains the user's authentication session's
# token.
SESSION_COOKIE_NAME = '__ccPrivilegedAccessToken'

# The newest supported minor version (value) for each supported major version
# (key) in this particular build.
SUPPORTED_VERSIONS = {
    6: 14
}

# Used by the client to automatically identify the latest major and minor
# version.
CLIENT_API = '{0}.{1}'.format(
    max(SUPPORTED_VERSIONS.keys()),
    SUPPORTED_VERSIONS[max(SUPPORTED_VERSIONS.keys())])


def get_version_str():
    return ', '.join(["v" + str(v) + "." + str(SUPPORTED_VERSIONS[v])
                      for v in SUPPORTED_VERSIONS])
