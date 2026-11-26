# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Mock bazel-remote server for the analysis cache tests.

It implements the part of the bazel-remote HTTP API which is used by the
CodeChecker server:
  PUT/GET /cas/<sha256>  Content Addressable Storage (the sha256 of the body
                         must match the key)
  PUT/GET /ac/<sha256>   Action Cache (the body must be a valid
                         ActionResult)

It does not reproduce every detail of bazel-remote (e.g. LRU eviction,
compression).
"""

import base64
import hashlib
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google.protobuf.message import DecodeError

from codechecker_server.analysis_cache import remote_execution_pb2 as reapi

_PATH_RE = re.compile(r'^/(cas|ac)/([0-9a-f]{64})$')


class MockBazelRemote:
    """
    Mock bazel-remote server running in a background thread.

    Test hooks:
      - cas / ac: the stored entries (dict: key -> bytes)
      - fail_status: if set, every request is answered with this status
      - delay: seconds to wait before answering every request
      - requests: the list of (method, path) of the received requests
    """

    def __init__(self, user=None, password=None):
        self.cas = {}
        self.ac = {}
        self.fail_status = None
        self.delay = 0
        self.requests = []
        self.user = user
        self.password = password
        self.lock = threading.Lock()

        mock = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def __reply(self, status, body=b''):
                self.send_response(status)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def __prepare(self):
                with mock.lock:
                    mock.requests.append((self.command, self.path))
                if mock.delay:
                    time.sleep(mock.delay)
                if mock.fail_status:
                    self.__reply(mock.fail_status)
                    return None
                if mock.user is not None:
                    expected = 'Basic ' + base64.b64encode(
                        f"{mock.user}:{mock.password}".encode()).decode()
                    if self.headers.get('Authorization') != expected:
                        self.__reply(401)
                        return None
                m = _PATH_RE.match(self.path)
                if not m:
                    self.__reply(400)
                    return None
                return m.group(1), m.group(2)

            def do_GET(self):  # pylint: disable=invalid-name
                target = self.__prepare()
                if not target:
                    return
                kind, key = target
                store = mock.cas if kind == 'cas' else mock.ac
                with mock.lock:
                    data = store.get(key)
                if data is None:
                    self.__reply(404)
                else:
                    self.__reply(200, data)

            def do_PUT(self):  # pylint: disable=invalid-name
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length else b''
                target = self.__prepare()
                if not target:
                    return
                kind, key = target
                if kind == 'cas':
                    if hashlib.sha256(body).hexdigest() != key:
                        self.__reply(400)
                        return
                    with mock.lock:
                        mock.cas[key] = body
                else:
                    try:
                        result = reapi.ActionResult.FromString(body)
                    except DecodeError:
                        self.__reply(400)
                        return
                    if any(not re.match(r'^[0-9a-f]{64}$', f.digest.hash)
                           for f in result.output_files):
                        self.__reply(400)
                        return
                    with mock.lock:
                        mock.ac[key] = body
                self.__reply(200)

        self.__server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.__thread = threading.Thread(target=self.__server.serve_forever,
                                         daemon=True)

    @property
    def url(self) -> str:
        host, port = self.__server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self):
        self.__thread.start()
        return self

    def stop(self):
        self.__server.shutdown()
        self.__server.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *_args):
        self.stop()
