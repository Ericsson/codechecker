# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Storage logic of the analysis cache: input validation, cache key computation
and the REAPI (ActionResult + CAS) storage format in bazel-remote.

The file contents are stored in the CAS in the form they were received on the
API (base64(zlib(file bytes))), and they are returned unchanged. The server
never decompresses them.
"""

import base64
import binascii
import hashlib
import re
from dataclasses import dataclass

from google.protobuf.message import DecodeError

from codechecker_common.logger import get_logger

from .bazel_remote import BazelRemoteClient
from . import remote_execution_pb2 as reapi

LOG = get_logger('server')

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_FILES_PER_ENTRY = 3
DEFAULT_MAX_CONTENT_SIZE = 20 * 1024 * 1024

# Upper limit of a serialized ActionResult read from the backend. An entry
# has only a few output files, so a few KiB would be enough.
MAX_ACTION_RESULT_SIZE = 1024 * 1024

KEY_RE = re.compile(r'^[0-9a-f]{64}$')
FILENAME_RE = re.compile(r'^[A-Za-z0-9._-]{1,255}$')


class CacheNotConfiguredError(Exception):
    """ The analysis cache is not configured on the server. """


class CacheValidationError(ValueError):
    """ The request is invalid. """


@dataclass(frozen=True)
class CacheConfig:
    url: str
    user: str | None = None
    password_file: str | None = None
    timeout: float = DEFAULT_TIMEOUT
    max_files_per_entry: int = DEFAULT_MAX_FILES_PER_ENTRY
    max_content_size: int = DEFAULT_MAX_CONTENT_SIZE

    @staticmethod
    def from_dict(cfg: dict | None) -> "CacheConfig":
        """
        Create the configuration from the 'analysis_cache' section of the
        server configuration. Raises CacheNotConfiguredError if there is no
        backend URL configured.
        """
        cfg = cfg or {}
        url = cfg.get('url')
        if not url:
            raise CacheNotConfiguredError("analysis cache is not configured")

        def _num(name, default, typ):
            value = cfg.get(name)
            if value is None:
                return default
            try:
                value = typ(value)
            except (TypeError, ValueError):
                LOG.warning("Invalid 'analysis_cache.%s' value in the server "
                            "configuration, using the default: %s",
                            name, default)
                return default
            return value if value > 0 else default

        return CacheConfig(
            url=url,
            user=cfg.get('user') or None,
            password_file=cfg.get('password_file') or None,
            timeout=_num('timeout', DEFAULT_TIMEOUT, float),
            max_files_per_entry=_num('max_files_per_entry',
                                     DEFAULT_MAX_FILES_PER_ENTRY, int),
            max_content_size=_num('max_content_size',
                                  DEFAULT_MAX_CONTENT_SIZE, int))


def ac_key(product_endpoint: str, analysis_key: str) -> str:
    """
    The bazel-remote Action Cache key of an analysis key in a product. The
    product endpoint is hashed into the key, so the products do not share
    their cache entries.
    """
    return hashlib.sha256(
        f"{product_endpoint}:{analysis_key}".encode('utf-8')).hexdigest()


def validate_key(key) -> str:
    if not isinstance(key, str) or not KEY_RE.match(key):
        raise CacheValidationError(
            "Invalid cache key: it must be a sha256 hex digest "
            "(64 lowercase hexadecimal characters).")
    return key


def is_valid_filename(filename) -> bool:
    return isinstance(filename, str) and \
        bool(FILENAME_RE.match(filename)) and filename not in ('.', '..')


def validate_contents(contents, config: CacheConfig) -> list[tuple[str, str]]:
    """
    Validate the content list of a writeCache request. Returns the list of
    (filename, encoded content) pairs.
    """
    if not contents:
        raise CacheValidationError("The content list is empty.")

    if len(contents) > config.max_files_per_entry:
        raise CacheValidationError(
            f"Too many files in the cache entry: {len(contents)} > "
            f"{config.max_files_per_entry}.")

    result = []
    seen = set()
    for item in contents:
        filename = getattr(item, 'filename', None)
        content = getattr(item, 'content', None)

        if not is_valid_filename(filename):
            raise CacheValidationError(
                f"Invalid filename: {filename!r}. It must be a plain file "
                "name (letters, digits, '.', '_', '-').")

        if filename in seen:
            raise CacheValidationError(f"Duplicated filename: {filename}.")
        seen.add(filename)

        if not isinstance(content, str):
            raise CacheValidationError(
                f"The content of '{filename}' is missing.")

        # Check the size first, before doing any work on the content.
        if len(content) > config.max_content_size:
            raise CacheValidationError(
                f"The content of '{filename}' is too large: "
                f"{len(content)} > {config.max_content_size} bytes.")

        try:
            base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError) as ex:
            raise CacheValidationError(
                f"The content of '{filename}' is not valid base64.") from ex

        result.append((filename, content))

    return result


def write_entry(client: BazelRemoteClient, product_endpoint: str,
                analysis_key: str, contents, config: CacheConfig):
    """
    Store the given contents for the analysis key: first every file into the
    CAS, then the ActionResult which refers them into the AC.
    """
    validate_key(analysis_key)
    files = validate_contents(contents, config)

    action_result = reapi.ActionResult(exit_code=0)
    for filename, content in files:
        data = content.encode('ascii')
        digest = hashlib.sha256(data).hexdigest()
        client.put_cas(digest, data)
        action_result.output_files.append(reapi.OutputFile(
            path=filename,
            digest=reapi.Digest(hash=digest, size_bytes=len(data))))

    # Only after all CAS uploads succeeded, so the AC entry does not refer to
    # a missing blob.
    client.put_ac(ac_key(product_endpoint, analysis_key),
                  action_result.SerializeToString())


def _parse_action_result(data: bytes, config: CacheConfig) \
        -> reapi.ActionResult | None:
    try:
        action_result = reapi.ActionResult.FromString(data)
    except DecodeError:
        return None

    files = action_result.output_files
    if not files or len(files) > config.max_files_per_entry:
        return None

    names = set()
    for f in files:
        if not is_valid_filename(f.path) or f.path in names:
            return None
        names.add(f.path)
        if not KEY_RE.match(f.digest.hash) or \
                not 0 <= f.digest.size_bytes <= config.max_content_size:
            return None

    return action_result


def read_entry(client: BazelRemoteClient, product_endpoint: str,
               analysis_key: str, config: CacheConfig) \
        -> list[tuple[str, str]]:
    """
    Read the cache entry of the analysis key. Returns the list of
    (filename, encoded content) pairs, or an empty list on cache miss.
    Partial entries are never returned.
    """
    validate_key(analysis_key)
    key = ac_key(product_endpoint, analysis_key)

    data = client.get_ac(key, MAX_ACTION_RESULT_SIZE)
    if data is None:
        return []

    action_result = _parse_action_result(data, config)
    if action_result is None:
        LOG.warning("Invalid analysis cache entry in the backend "
                    "(AC key: %s), it is handled as a cache miss.", key)
        return []

    result = []
    for f in action_result.output_files:
        blob = client.get_cas(f.digest.hash, config.max_content_size)
        if blob is None:
            # E.g. evicted by the LRU of bazel-remote.
            LOG.debug("CAS blob %s of AC entry %s is missing.",
                      f.digest.hash, key)
            return []

        if len(blob) != f.digest.size_bytes or \
                hashlib.sha256(blob).hexdigest() != f.digest.hash:
            LOG.warning("Digest mismatch of CAS blob %s (AC key: %s), it is "
                        "handled as a cache miss.", f.digest.hash, key)
            return []

        try:
            content = blob.decode('ascii')
        except UnicodeDecodeError:
            LOG.warning("Invalid content of CAS blob %s (AC key: %s), it is "
                        "handled as a cache miss.", f.digest.hash, key)
            return []

        result.append((f.path, content))

    return result
