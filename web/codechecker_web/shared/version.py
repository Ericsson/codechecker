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
# DEPRECATED: Session-based authentication will be removed in a future version.
# Use the Authorization header instead.
SESSION_COOKIE_NAME = '__ccPrivilegedAccessToken'

# The newest supported minor version (value) for each supported major version
# (key) in this particular build.
SUPPORTED_VERSIONS = {
    6: 59
}

# Used by the client to automatically identify the latest major and minor
# version.
CLIENT_API = \
    f'{max(SUPPORTED_VERSIONS.keys())}.' \
    f'{SUPPORTED_VERSIONS[max(SUPPORTED_VERSIONS.keys())]}'


def get_version_str():
    return ', '.join(f"v{str(major)}.{str(minor)}"
                     for major, minor in SUPPORTED_VERSIONS.items())
