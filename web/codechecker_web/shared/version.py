# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
This module stores constants that are shared between the CodeChecker server
and client, related to API and other version-specific information.
"""


# The name of the cookie which contains the user's authentication session's
# token.
SESSION_COOKIE_NAME = '__ccPrivilegedAccessToken'

# The newest supported minor version (value) for each supported major version
# (key) in this particular build.
SUPPORTED_VERSIONS = {
    6: 50
}

# Used by the client to automatically identify the latest major and minor
# version.
CLIENT_API = '{0}.{1}'.format(
    max(SUPPORTED_VERSIONS.keys()),
    SUPPORTED_VERSIONS[max(SUPPORTED_VERSIONS.keys())])


def get_version_str():
    return ', '.join(["v" + str(v) + "." + str(SUPPORTED_VERSIONS[v])
                      for v in SUPPORTED_VERSIONS])
