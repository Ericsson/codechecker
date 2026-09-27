# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Exercise the Docker health probe against real HTTP and TLS sockets."""

from functools import partial
import http.server
import importlib.util
from pathlib import Path
import ssl
import threading
import unittest


WEB_ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "healthcheck", WEB_ROOT / "docker" / "healthcheck.py")
HEALTHCHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HEALTHCHECK)


class LiveHandler(http.server.BaseHTTPRequestHandler):
    """Serve only the liveness route with a configurable HTTP status."""

    def __init__(self, *args, status=200, **kwargs):
        self.status = status
        super().__init__(*args, **kwargs)

    def do_GET(self):  # pylint: disable=invalid-name
        """Respond to a liveness request without a body."""
        self.send_response(self.status if self.path == "/live" else 404)
        self.end_headers()


class DockerHealthcheckTest(unittest.TestCase):
    """Check both protocols and preserve failure reporting."""

    def test_liveness(self):
        """Accept healthy HTTP/HTTPS and reject server error responses."""
        for tls in (False, True):
            for status in (200, 500):
                with self.subTest(tls=tls, status=status):
                    handler = partial(LiveHandler, status=status)
                    with http.server.ThreadingHTTPServer(
                            ("127.0.0.1", 0), handler) as server:
                        if tls:
                            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                            fixtures = WEB_ROOT / "tests" / "ssl_example_cert"
                            context.load_cert_chain(fixtures / "cert.pem",
                                                    fixtures / "key.pem")
                            server.socket = context.wrap_socket(
                                server.socket, server_side=True)
                        worker = threading.Thread(target=server.serve_forever,
                                                  daemon=True)
                        worker.start()
                        try:
                            self.assertEqual(
                                HEALTHCHECK.healthy(server.server_port),
                                status == 200)
                        finally:
                            server.shutdown()
                            worker.join()

    def test_stopped_server(self):
        """A closed listening socket must not report a healthy container."""
        with http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), LiveHandler) as server:
            port = server.server_port
        self.assertFalse(HEALTHCHECK.healthy(port))
