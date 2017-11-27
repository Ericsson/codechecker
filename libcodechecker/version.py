# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
This module stores a global constant between CodeChecker server and client,
which dictates what API version the client should use, and what the server
accepts.
"""

# This dict object stores for each MAJOR version (key) the largest MINOR
# version (value) supported by the build.
SUPPORTED_VERSIONS = {
    6: 4
}

# This value is automatically generated to represent the highest version
# available in the current build.
CLIENT_API = '{0}.{1}'.format(
    max(SUPPORTED_VERSIONS.keys()),
    SUPPORTED_VERSIONS[max(SUPPORTED_VERSIONS.keys())])
