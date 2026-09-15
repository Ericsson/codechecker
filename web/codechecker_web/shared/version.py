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
