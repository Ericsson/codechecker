# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Minimal HTTP client of the bazel-remote cache server.

Only the HTTP API is used:
  - Content Addressable Storage (CAS): GET/PUT /cas/<sha256>
  - Action Cache (AC):                 GET/PUT /ac/<sha256>
"""

import threading

import requests

from codechecker_common.logger import get_logger

LOG = get_logger('server')


class BazelRemoteError(Exception):
    """
    The bazel-remote backend is not available or returned an unexpected
    response.
    """


class BazelRemoteClient:
    """
    HTTP client of a bazel-remote instance. Not found entries are returned
    as None, every other failure raises BazelRemoteError.
    """

    def __init__(self, url: str, user: str | None = None,
                 password: str | None = None, timeout: float = 30):
        self.__url = url.rstrip('/')
        self.__timeout = (timeout, timeout)
        self.__session = requests.Session()
        if user:
            self.__session.auth = (user, password or '')

    @property
    def url(self) -> str:
        return self.__url

    def __get(self, kind: str, key: str, max_size: int) -> bytes | None:
        url = f"{self.__url}/{kind}/{key}"
        try:
            with self.__session.get(url, timeout=self.__timeout,
                                    stream=True) as resp:
                if resp.status_code == 404:
                    return None
                if resp.status_code != 200:
                    raise BazelRemoteError(
                        f"GET /{kind}/{key} failed: HTTP {resp.status_code}")

                # Read the body with a size limit, so a broken or malicious
                # backend can not exhaust the memory of the server.
                data = bytearray()
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    data.extend(chunk)
                    if len(data) > max_size:
                        raise BazelRemoteError(
                            f"GET /{kind}/{key}: the response is larger "
                            f"than {max_size} bytes")
                return bytes(data)
        except requests.RequestException as ex:
            raise BazelRemoteError(f"GET /{kind}/{key} failed: {ex}") from ex

    def __put(self, kind: str, key: str, data: bytes):
        url = f"{self.__url}/{kind}/{key}"
        try:
            resp = self.__session.put(
                url, data=data, timeout=self.__timeout,
                headers={'Content-Type': 'application/octet-stream'})
        except requests.RequestException as ex:
            raise BazelRemoteError(f"PUT /{kind}/{key} failed: {ex}") from ex

        if not 200 <= resp.status_code < 300:
            raise BazelRemoteError(
                f"PUT /{kind}/{key} failed: HTTP {resp.status_code} "
                f"{resp.text[:200]}")

    def get_cas(self, sha256: str, max_size: int) -> bytes | None:
        return self.__get('cas', sha256, max_size)

    def put_cas(self, sha256: str, data: bytes):
        self.__put('cas', sha256, data)

    def get_ac(self, key: str, max_size: int) -> bytes | None:
        return self.__get('ac', key, max_size)

    def put_ac(self, key: str, data: bytes):
        self.__put('ac', key, data)


_CLIENTS: dict[tuple, BazelRemoteClient] = {}
_CLIENTS_LOCK = threading.Lock()


def get_client(url: str, user: str | None, password_file: str | None,
               timeout: float) -> BazelRemoteClient:
    """
    Returns a (per process cached) client for the given configuration, so the
    HTTP connections to the backend are reused between the requests.
    """
    password = None
    if user and password_file:
        try:
            with open(password_file, 'r', encoding='utf-8') as f:
                password = f.read().strip()
        except OSError as ex:
            raise BazelRemoteError(
                "Failed to read the bazel-remote password file "
                f"'{password_file}': {ex}") from ex

    cfg = (url, user, password, timeout)
    with _CLIENTS_LOCK:
        client = _CLIENTS.get(cfg)
        if client is None:
            LOG.debug("Creating bazel-remote client for %s", url)
            client = BazelRemoteClient(url, user, password, timeout)
            _CLIENTS[cfg] = client
        return client
