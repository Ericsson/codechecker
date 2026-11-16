# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Client side of the server-side analysis cache (central library which can be
used by all analyzer plugins).

This module does not depend on the web client (Thrift). The Thrift client
(codechecker_client.analysis_cache_client) is imported lazily, only if
caching is turned on.

Cache key:
  analysis_key = sha256("v1:" + analysis_invocation_key + ":" +
                        preprocessed_source_key + ":" + analyzer_binary_key)
"""

import base64
import hashlib
import importlib
import os
import re
import shlex
import subprocess
import tempfile
import zlib
from dataclasses import dataclass, field
from xml.sax.saxutils import escape as xml_escape

from codechecker_common.logger import get_logger

LOG = get_logger('analyzer')

# Version of the cache entry format. Bumping it invalidates every existing
# cache entry.
CACHE_FORMAT_VERSION = "v1"

SOURCE_ROOT_PLACEHOLDER = "__SOURCE_ROOT__"
ANALYZER_PLACEHOLDER = "<ANALYZER>"
OUTPUT_PLACEHOLDER = "<OUTPUT>"

# Fixed role names of the files of a cache entry.
ROLE_RESULT = "result.plist"
ROLE_STDOUT = "stdout.txt"
ROLE_STDERR = "stderr.txt"
ROLES = (ROLE_RESULT, ROLE_STDOUT, ROLE_STDERR)

# Maximum (decompressed) size of a cached file. Larger results are not
# written into the cache, and larger responses are rejected (zip bomb
# protection).
MAX_FILE_SIZE = 20 * 1024 * 1024

# Timeouts of the AnalysisCache API calls (seconds).
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 30

# A worker stops using the cache after this many consecutive errors.
MAX_CONSECUTIVE_ERRORS = 3

CLIENT_MODULE = "codechecker_client.analysis_cache_client"


class CacheContentError(ValueError):
    """ Invalid cache content (e.g. too large, broken encoding). """


# ---------------------------------------------------------------------------
# Source root replacement.
# ---------------------------------------------------------------------------

# Characters which may follow the source root, so that only whole path
# prefixes are replaced: path separators, quotes, whitespace, the start of the
# next XML element or entity. (e.g. with source root '/work/src',
# '/work/src2/a.cpp' is not changed.)
_ROOT_FOLLOWER = r'(?=[/\\"\'\s<&]|$)'


def normalize_source_root(path: str) -> str:
    """
    Normalize the user given source root: absolute path without a trailing
    path separator. Symbolic links are not resolved.
    """
    return os.path.normpath(os.path.abspath(path))


def _root_regex(root: str) -> re.Pattern:
    return re.compile(re.escape(root) + _ROOT_FOLLOWER)


def _root_regex_bytes(root: bytes) -> re.Pattern:
    return re.compile(re.escape(root) + _ROOT_FOLLOWER.encode())


def replace_source_root(text: str, source_root: str | None) -> str:
    """ Replace the source root with the placeholder in a text. """
    if not source_root:
        return text
    return _root_regex(source_root).sub(SOURCE_ROOT_PLACEHOLDER, text)


def replace_source_root_bytes(data: bytes, source_root: str | None) -> bytes:
    """ Replace the source root with the placeholder in binary data. """
    if not source_root:
        return data
    return _root_regex_bytes(os.fsencode(source_root)).sub(
        SOURCE_ROOT_PLACEHOLDER.encode(), data)


def replace_source_root_in_plist(data: bytes,
                                 source_root: str | None) -> bytes:
    """
    Replace the source root with the placeholder in a plist (XML) file. The
    source root is matched in its XML escaped form.
    """
    if not source_root:
        return data
    return replace_source_root_bytes(data, xml_escape(source_root))


def restore_source_root_in_plist(data: bytes,
                                 source_root: str | None) -> bytes:
    """
    Replace the placeholder back with the (XML escaped) source root of the
    current run in a plist file.
    """
    if not source_root:
        return data
    return data.replace(SOURCE_ROOT_PLACEHOLDER.encode(),
                        os.fsencode(xml_escape(source_root)))


# ---------------------------------------------------------------------------
# Keys.
# ---------------------------------------------------------------------------

def sanitize_analyzer_cmd(analyzer_cmd: list[str],
                          source_root: str | None) -> list[str]:
    """
    Remove the location dependent parts of an analyzer command:
      - the analyzer binary (first argument) is replaced with <ANALYZER>,
      - the value of the -o (output file) argument is replaced with <OUTPUT>,
      - the source root is replaced with __SOURCE_ROOT__.
    The given list is not modified.
    """
    if not analyzer_cmd:
        return []

    result = [ANALYZER_PLACEHOLDER]
    args = iter(analyzer_cmd[1:])
    for arg in args:
        if arg == '-o':
            result.append(arg)
            if next(args, None) is not None:
                result.append(OUTPUT_PLACEHOLDER)
            continue
        if arg.startswith('-o') and len(arg) > 2 and \
                not arg.startswith('--'):
            result.append('-o' + OUTPUT_PLACEHOLDER)
            continue
        result.append(replace_source_root(arg, source_root))

    return result


def analysis_invocation_key(analyzer_cmd: list[str],
                            source_root: str | None) -> str:
    """
    The sanitized analysis invocation string (see sanitize_analyzer_cmd()).
    """
    return shlex.join(sanitize_analyzer_cmd(analyzer_cmd, source_root))


# Line marker of the preprocessor output, e.g. '# 12 "a.h" 2' or
# '#line 12 "a.h"'. Groups: line number, file name, the rest (flags).
LINE_MARKER_PATTERN = re.compile(
    rb'^#\s*(?:line\s+)?([0-9]+)(\s+"(?:[^"\\]|\\.)*")?(.*?)(\r?\n)?$',
    re.DOTALL)


def strip_line_marker_file_names(data: bytes) -> bytes:
    """
    Remove the file names from the line markers of the preprocessed output
    ('# 12 "/x/a.h" 2' -> '# 12 2'). The line numbers and the flags are kept,
    so a change which shifts lines changes the key. Other lines (e.g.
    '#pragma') are kept unchanged.
    """
    result = []
    for line in data.splitlines(keepends=True):
        match = LINE_MARKER_PATTERN.match(line) \
            if line.startswith(b'#') else None
        if match:
            newline = match.group(4) or b''
            line = b'# ' + match.group(1) + match.group(3) + newline
        result.append(line)
    return b''.join(result)


def preprocessed_source_key(preprocess_cmd: list[str], cwd: str | None,
                            env: dict | None,
                            source_root: str | None) -> str | None:
    """
    Run the preprocessor command and return the sha256 hex digest of its
    output (file names removed from the line markers, the source root
    replaced).
    Returns None if preprocessing failed.
    """
    try:
        proc = subprocess.run(preprocess_cmd, cwd=cwd, env=env,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=False)
    except OSError as ex:
        LOG.debug("Preprocessing failed: %s", ex)
        return None

    if proc.returncode != 0:
        LOG.debug("Preprocessing failed (%d): %s", proc.returncode,
                  shlex.join(preprocess_cmd))
        LOG.debug(proc.stderr.decode('utf-8', errors='replace'))
        return None

    output = replace_source_root_bytes(
        strip_line_marker_file_names(proc.stdout), source_root)
    return hashlib.sha256(output).hexdigest()


def analyzer_binary_key(analyzer_binary: str, env: dict | None) -> str | None:
    """
    sha256 of the full '<analyzer binary> --version' output. Compiler
    wrappers (e.g. ccache) forward --version to the real compiler.
    Returns None if the version could not be queried.
    """
    try:
        proc = subprocess.run([analyzer_binary, '--version'], env=env,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=False)
    except OSError as ex:
        LOG.debug("Failed to get the analyzer version: %s", ex)
        return None

    if proc.returncode != 0 or not proc.stdout:
        return None
    return hashlib.sha256(proc.stdout).hexdigest()


def compute_analysis_key(invocation_key: str, preprocessed_key: str,
                         binary_key: str) -> str:
    return hashlib.sha256(
        f"{CACHE_FORMAT_VERSION}:{invocation_key}:{preprocessed_key}:"
        f"{binary_key}".encode('utf-8', errors='surrogateescape')).hexdigest()


# ---------------------------------------------------------------------------
# Content encoding.
# ---------------------------------------------------------------------------

def encode_content(data: bytes) -> str:
    """ base64(zlib(data)) """
    return base64.b64encode(zlib.compress(data)).decode('ascii')


def decode_content(content: str, max_size: int = MAX_FILE_SIZE) -> bytes:
    """
    Decode a base64(zlib()) encoded content. The decompression is done with
    an output size limit, so a highly compressed input is rejected before it
    is fully decompressed into memory.
    """
    try:
        compressed = base64.b64decode(content, validate=True)
    except (ValueError, TypeError) as ex:
        raise CacheContentError("invalid base64 content") from ex

    decompressor = zlib.decompressobj()
    try:
        data = decompressor.decompress(compressed, max_size + 1)
    except zlib.error as ex:
        raise CacheContentError("invalid zlib content") from ex

    if len(data) > max_size or decompressor.unconsumed_tail:
        raise CacheContentError(
            f"the decompressed content is larger than {max_size} bytes")
    if not decompressor.eof:
        raise CacheContentError("truncated zlib content")

    return data


# ---------------------------------------------------------------------------
# Safe write into the report directory.
# ---------------------------------------------------------------------------

def is_inside_dir(path: str, directory: str) -> bool:
    real_dir = os.path.realpath(directory)
    real_path = os.path.realpath(path)
    try:
        return os.path.commonpath([real_path, real_dir]) == real_dir
    except ValueError:
        # E.g. paths on different drives on Windows.
        return False


def safe_write_file(report_dir: str, target: str, data: bytes) -> bool:
    """
    Write the data to the target path, only if the target is inside the
    report directory. The file is written to a temporary file next to the
    target, then moved to its place with os.replace(), so an existing
    symbolic link at the target path is replaced, not followed.
    Returns False if the target is outside of the report directory.
    """
    parent = os.path.realpath(os.path.dirname(os.path.abspath(target)))
    if not is_inside_dir(parent, report_dir):
        LOG.warning("Analysis cache: the target '%s' is outside of the report "
                    "directory '%s', the cached result is not used.",
                    target, report_dir)
        return False

    final_path = os.path.join(parent, os.path.basename(target))
    fd, tmp_path = tempfile.mkstemp(dir=parent, prefix='.cache_',
                                    suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(tmp_path, final_path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    return True


# ---------------------------------------------------------------------------
# Settings and worker side cache access.
# ---------------------------------------------------------------------------

@dataclass
class CacheSettings:
    """
    Picklable settings of the analysis cache which are passed to the analysis
    worker processes.
    """
    protocol: str
    host: str
    port: int
    product: str
    session_token: str | None
    source_root: str
    report_dir: str
    # analyzer name -> analyzer_binary_key
    binary_keys: dict = field(default_factory=dict)


@dataclass
class CacheEntry:
    """ The decoded content of a cache entry. """
    result: bytes
    stdout: str = ''
    stderr: str = ''


class CacheSession:
    """
    Cache access of one worker process. Every error is handled as a cache
    miss (fail open). After MAX_CONSECUTIVE_ERRORS consecutive errors the
    session stops using the cache.
    """

    def __init__(self, settings: CacheSettings):
        self.settings = settings
        self.__client = None
        self.__errors = 0
        self.disabled = False

    def __get_client(self):
        if self.__client is None:
            module = importlib.import_module(CLIENT_MODULE)
            s = self.settings
            self.__client = module.AnalysisCacheClient(
                s.protocol, s.host, s.port, s.product, s.session_token,
                CONNECT_TIMEOUT, READ_TIMEOUT)
        return self.__client

    def __error(self, operation: str, ex: Exception):
        self.__errors += 1
        LOG.debug("Analysis cache %s failed: %s", operation, ex)
        if self.__errors >= MAX_CONSECUTIVE_ERRORS and not self.disabled:
            self.disabled = True
            LOG.warning("The analysis cache is not used anymore by this "
                        "worker after %d consecutive errors (last error: "
                        "%s).", self.__errors, ex)

    def read(self, key: str) -> CacheEntry | None:
        """ Returns the cache entry of the key or None on cache miss. """
        if self.disabled:
            return None
        try:
            contents = self.__get_client().read_cache(key)
        except Exception as ex:
            self.__error('read', ex)
            return None
        self.__errors = 0

        files = {name: content for name, content in contents
                 if name in ROLES}
        if ROLE_RESULT not in files:
            return None

        try:
            result = decode_content(files[ROLE_RESULT])
            stdout = decode_content(files[ROLE_STDOUT]) \
                if ROLE_STDOUT in files else b''
            stderr = decode_content(files[ROLE_STDERR]) \
                if ROLE_STDERR in files else b''
        except CacheContentError as ex:
            LOG.warning("Invalid analysis cache entry %s: %s, it is handled "
                        "as a cache miss.", key, ex)
            return None

        result = restore_source_root_in_plist(result,
                                              self.settings.source_root)
        return CacheEntry(result=result,
                          stdout=stdout.decode('utf-8', errors='ignore'),
                          stderr=stderr.decode('utf-8', errors='ignore'))

    def write(self, key: str, result: bytes, stdout: str, stderr: str,
              source_name: str = '') -> bool:
        """
        Store the raw analyzer outputs. Returns True if the entry was stored.
        """
        if self.disabled:
            return False

        stdout_b = (stdout or '').encode('utf-8', errors='ignore')
        stderr_b = (stderr or '').encode('utf-8', errors='ignore')
        largest = max(len(result), len(stdout_b), len(stderr_b))
        if largest > MAX_FILE_SIZE:
            LOG.warning("Analysis result of %s is too large for the analysis "
                        "cache (%.1f MiB > %d MiB), it is not cached.",
                        source_name or key, largest / (1024 * 1024),
                        MAX_FILE_SIZE // (1024 * 1024))
            return False

        result = replace_source_root_in_plist(result,
                                              self.settings.source_root)
        contents = [(ROLE_RESULT, encode_content(result)),
                    (ROLE_STDOUT, encode_content(stdout_b)),
                    (ROLE_STDERR, encode_content(stderr_b))]
        try:
            self.__get_client().write_cache(key, contents)
        except Exception as ex:
            self.__error('write', ex)
            return False
        self.__errors = 0
        return True


def setup_cache(url: str, source_root: str, report_dir: str,
                analyzer_binaries: dict, env_for_bin) -> CacheSettings | None:
    """
    Set up the analysis cache in the main process, before the analysis
    workers are started: authenticate to the server and compute the
    analyzer binary keys. Returns None (and prints a warning) if the cache
    can not be used; the analysis continues without the cache.

    :param analyzer_binaries: analyzer name -> analyzer binary path.
    :param env_for_bin: function which returns the environment of a binary.
    """
    module = importlib.import_module(CLIENT_MODULE)

    try:
        protocol, host, port, product, token = module.authenticate(url)
    except SystemExit:
        LOG.warning("Analysis cache: authentication to '%s' failed, the "
                    "analysis continues without the cache.", url)
        return None
    except Exception as ex:
        LOG.warning("Analysis cache: failed to connect to '%s' (%s), the "
                    "analysis continues without the cache.", url, ex)
        return None

    binary_keys = {}
    for name, binary in analyzer_binaries.items():
        if not binary:
            continue
        key = analyzer_binary_key(binary, env_for_bin(binary))
        if key:
            binary_keys[name] = key
        else:
            LOG.warning("Analysis cache: failed to get the version of the "
                        "%s analyzer (%s), it is analyzed without the cache.",
                        name, binary)

    if not binary_keys:
        return None

    return CacheSettings(protocol=protocol, host=host, port=port,
                         product=product, session_token=token,
                         source_root=normalize_source_root(source_root),
                         report_dir=os.path.abspath(report_dir),
                         binary_keys=binary_keys)


def is_web_client_available() -> bool:
    """ Whether the web client (needed for the cache) is installed. """
    try:
        importlib.import_module(CLIENT_MODULE)
        return True
    except ImportError:
        return False
