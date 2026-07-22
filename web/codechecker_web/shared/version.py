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

API Versioning Strategy
-----------------------
CodeChecker uses a two-level versioning scheme for its Thrift API:
**MAJOR.MINOR** (e.g. ``6.72``).

- **MAJOR version** identifies the protocol generation. All current endpoints
  share the same major version (v6). A major bump would indicate a
  fundamentally incompatible protocol change.
- **MINOR version** is incremented when new Thrift methods are added or
  existing method signatures are extended. The server accepts any client
  whose minor version is <= the server's supported minor version for that
  major, ensuring backward compatibility.

The npm and PyPI packages use a three-part semver (``6.72.0``) because those
ecosystems require it. The **patch component is always 0** and is never used
in version negotiation — it is stripped before constructing API URLs or
performing compatibility checks.

Version flow through the system:
1. The client constructs a URL with ``/v<MAJOR.MINOR>/`` from CLIENT_API.
2. ``routing.py`` parses the version tag, validates major.minor against
   SUPPORTED_VERSIONS, and returns a ``(major, minor)`` tuple.
3. ``server.py`` dispatches to the appropriate handler based on the major
   version (currently only v6 exists).
4. Individual handlers (e.g. ``report_server.py``) may branch on the full
   ``(major, minor)`` tuple for backward-compatible behavioral changes
   introduced at a specific minor version.
"""


# The name of the cookie which contains the user's authentication session's
# token.
# DEPRECATED: Session-based authentication will be removed in a future version.
# Use the Authorization header instead.
SESSION_COOKIE_NAME = '__ccPrivilegedAccessToken'

# The newest supported minor version (value) for each supported major version
# (key) in this particular build.
SUPPORTED_VERSIONS = {
    6: 72
}

# Used by the client to automatically identify the latest major and minor
# version. This string is used in API URL paths (e.g. "/v6.72/Tasks").
CLIENT_API = \
    f'{max(SUPPORTED_VERSIONS.keys())}.' \
    f'{SUPPORTED_VERSIONS[max(SUPPORTED_VERSIONS.keys())]}'


def get_version_str():
    return ', '.join(f"v{str(major)}.{str(minor)}"
                     for major, minor in SUPPORTED_VERSIONS.items())
