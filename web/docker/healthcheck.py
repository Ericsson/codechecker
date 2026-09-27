# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Probe the container's local HTTP or HTTPS liveness endpoint."""

import http.client
import ssl
import sys


def healthy(port=8001):
    """Check the local liveness endpoint over HTTP, then HTTPS."""
    # This probe stays on loopback and sends no credentials. Certificates may
    # be self-signed or issued for the external hostname instead of loopback.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    connections = (
        http.client.HTTPConnection("127.0.0.1", port, timeout=2),
        http.client.HTTPSConnection("127.0.0.1", port, timeout=2,
                                    context=context),
    )
    for connection in connections:
        try:
            connection.request("GET", "/live")
            if connection.getresponse().status == 200:
                return True
        except (OSError, http.client.HTTPException):
            pass
        finally:
            connection.close()
    return False


if __name__ == "__main__":
    sys.exit(0 if healthy() else 1)
